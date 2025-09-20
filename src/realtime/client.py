#!/usr/bin/env python3
"""
OpenAI Realtime API WebSocket client with streaming support.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config.env import get_settings
from ..integrations.yclients_adapter import YClientsAdapter
from ..utils.logger import get_logger
from .events import (
    ConversationItem,
    ConversationItemCreateEvent,
    EventType,
    IncomingEvent,
    InputTextContent,
    ResponseCancelEvent,
    ResponseCreateEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    Role,
    SessionConfig,
    SessionUpdateEvent,
    StreamController,
    StreamState,
)
from .tools import get_system_instructions, get_tools

logger = get_logger(__name__)
settings = get_settings()


class OpenAIRealtimeClient:
    """OpenAI Realtime API WebSocket client for a single user session."""
    
    def __init__(self, yclients_adapter: YClientsAdapter, user_id: int):
        self.yclients_adapter = yclients_adapter
        self.user_id = user_id  # Каждый клиент привязан к конкретному пользователю
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.active_streams: Dict[int, StreamController] = {}
        self.pending_function_calls: Dict[str, Dict[str, Any]] = {}
        self._connection_task: Optional[asyncio.Task] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._should_reconnect = True
        self._last_pong_time: Optional[datetime] = None  # Set only after first successful pong
        self._created_at = datetime.utcnow()
        self._reconnecting = False  # Prevent multiple reconnection tasks
        self._last_reconnect_time: Optional[datetime] = None
        self._consecutive_failures = 0
        self._circuit_breaker_open = False
        self._circuit_breaker_open_time: Optional[datetime] = None
        
        logger.info(f"🔗 Created dedicated OpenAI client for user {user_id}")
        
    async def connect(self) -> None:
        """Connect to OpenAI Realtime API."""
        if self.is_connected and self.websocket and not self.websocket.closed:
            logger.debug("Already connected to Realtime API")
            return
            
        try:
            logger.info(f"Connecting to OpenAI Realtime API... (attempt {self._reconnect_attempts + 1})")
            
            # Cancel existing tasks
            await self._cleanup_tasks()
            
            self.websocket = await websockets.connect(
                settings.get_realtime_ws_url(),
                extra_headers=settings.get_realtime_headers(),
                ping_interval=settings.WS_PING_INTERVAL,
                ping_timeout=settings.WS_PING_TIMEOUT,
                close_timeout=settings.WS_CONNECT_TIMEOUT,
                max_size=2**20,  # 1MB max message size
                compression=None,  # Disable compression for better performance
            )
            
            self.is_connected = True
            self._reconnect_attempts = 0
            logger.info("Connected to OpenAI Realtime API")
            
            # Initialize session
            await self._initialize_session()
            
            # Start listening for events
            self._listen_task = asyncio.create_task(self._listen_events())
            
            # Start connection monitoring
            self._monitor_task = asyncio.create_task(self._monitor_connection())
            
        except Exception as e:
            logger.error(f"Failed to connect to Realtime API: {e}")
            self.is_connected = False
            self._reconnect_attempts += 1
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from OpenAI Realtime API."""
        self._should_reconnect = False
        self._reconnecting = False  # Reset reconnection flag
        self._circuit_breaker_open = False  # Reset circuit breaker
        self._circuit_breaker_open_time = None
        self._consecutive_failures = 0
        
        if self.websocket and not self.websocket.closed:
            logger.info("Disconnecting from OpenAI Realtime API...")
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
        
        await self._cleanup_tasks()
        
        self.is_connected = False
        self.active_streams.clear()
        self.pending_function_calls.clear()
        
    async def _cleanup_tasks(self) -> None:
        """Clean up background tasks."""
        tasks_to_cancel = [
            ("listen", self._listen_task),
            ("connection", self._connection_task),
            ("monitor", self._monitor_task),
        ]
        
        for task_name, task in tasks_to_cancel:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.warning(f"Error cancelling {task_name} task: {e}")
    
    async def _monitor_connection(self) -> None:
        """Monitor WebSocket connection health."""
        logger.info("🔍 Started connection monitoring")
        
        # Initialize last pong time to now when monitoring starts
        self._last_pong_time = datetime.utcnow()
        
        while self._should_reconnect and self.is_connected:
            try:
                # Check if websocket is still alive
                if not self.websocket or self.websocket.closed:
                    logger.warning("💔 WebSocket is closed, triggering reconnection")
                    self.is_connected = False
                    await self._trigger_reconnection()
                    break
                
                # Check if we haven't received pong for too long (only if we've sent pings before)
                if self._last_pong_time:
                    time_since_pong = (datetime.utcnow() - self._last_pong_time).total_seconds()
                    max_pong_wait = settings.WS_PING_TIMEOUT * 3  # Allow 3x timeout before considering dead
                    if time_since_pong > max_pong_wait:
                        logger.warning(f"⏰ No pong received for {time_since_pong:.1f}s (max: {max_pong_wait}s), connection may be dead")
                        self.is_connected = False
                        await self._trigger_reconnection()
                        break
                
                # Send ping to check connection
                try:
                    pong_waiter = await self.websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=settings.WS_PING_TIMEOUT)
                    self._last_pong_time = datetime.utcnow()
                    logger.debug("✅ Ping/pong successful")
                except asyncio.TimeoutError:
                    logger.warning(f"⏱️ Ping timeout after {settings.WS_PING_TIMEOUT}s, connection may be dead")
                    self.is_connected = False
                    await self._trigger_reconnection()
                    break
                except Exception as e:
                    logger.warning(f"❌ Ping failed: {e}")
                    self.is_connected = False
                    await self._trigger_reconnection()
                    break
                
                # Wait before next check
                await asyncio.sleep(settings.WS_PING_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("Connection monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"💥 Error in connection monitoring: {e}")
                await asyncio.sleep(5)  # Wait before retrying
        
        logger.info("Connection monitoring stopped")
    
    async def _trigger_reconnection(self) -> None:
        """Trigger reconnection if not already in progress."""
        if self._reconnecting:
            logger.debug("Reconnection already in progress, skipping")
            return
            
        self._reconnecting = True
        self._connection_task = asyncio.create_task(self._reconnect())
    
    async def _reconnect(self) -> None:
        """Reconnect to WebSocket with exponential backoff and circuit breaker."""
        try:
            if not self._should_reconnect:
                logger.info("Reconnection disabled, not attempting to reconnect")
                return
            
            # Check circuit breaker
            if self._circuit_breaker_open:
                if self._circuit_breaker_open_time:
                    time_since_open = (datetime.utcnow() - self._circuit_breaker_open_time).total_seconds()
                    # Try to close circuit breaker after 5 minutes
                    if time_since_open < 300:
                        logger.warning(f"🚫 Circuit breaker open, skipping reconnection (will retry in {300 - time_since_open:.0f}s)")
                        return
                    else:
                        logger.info("🔧 Attempting to close circuit breaker")
                        self._circuit_breaker_open = False
                        self._consecutive_failures = 0
                
            if self._reconnect_attempts >= self._max_reconnect_attempts:
                logger.error(f"❌ Max reconnection attempts ({self._max_reconnect_attempts}) reached, opening circuit breaker")
                self._circuit_breaker_open = True
                self._circuit_breaker_open_time = datetime.utcnow()
                self._should_reconnect = False
                return
            
            # Check if we're reconnecting too frequently
            if self._last_reconnect_time:
                time_since_last = (datetime.utcnow() - self._last_reconnect_time).total_seconds()
                if time_since_last < 5:  # Less than 5 seconds since last attempt
                    self._consecutive_failures += 1
                    if self._consecutive_failures > 5:
                        logger.warning(f"🚫 Too many consecutive failures ({self._consecutive_failures}), opening circuit breaker")
                        self._circuit_breaker_open = True
                        self._circuit_breaker_open_time = datetime.utcnow()
                        return
            
            # Exponential backoff with jitter and circuit breaker consideration
            base_delay = min(2 ** self._reconnect_attempts, 60)  # Max 60 seconds
            if self._consecutive_failures > 0:
                base_delay += self._consecutive_failures * 5  # Add 5s per consecutive failure
                
            # Add some jitter to avoid thundering herd
            import random
            jitter = random.uniform(0.1, 0.3) * base_delay
            delay = base_delay + jitter
            
            logger.warning(f"⏳ Attempting to reconnect in {delay:.1f}s... (attempt {self._reconnect_attempts + 1}/{self._max_reconnect_attempts}, failures: {self._consecutive_failures})")
            
            await asyncio.sleep(delay)
            
            # Check if we should still reconnect after delay
            if not self._should_reconnect:
                logger.info("Reconnection disabled during delay, aborting")
                return
            
            self._last_reconnect_time = datetime.utcnow()
            
            try:
                await self.connect()
                logger.info("✅ Successfully reconnected to Realtime API")
                
                # Reset failure counters on successful connection
                self._consecutive_failures = 0
                self._circuit_breaker_open = False
                self._circuit_breaker_open_time = None
                
                # Restore any active streams if needed
                if self.active_streams:
                    logger.info(f"🔄 Restoring {len(self.active_streams)} active streams")
                    
            except Exception as e:
                logger.error(f"❌ Reconnection attempt failed: {e}")
                self._consecutive_failures += 1
                
                if self._should_reconnect:
                    # Schedule another reconnection attempt
                    self._reconnect_attempts += 1
                    await self._trigger_reconnection()
        finally:
            self._reconnecting = False
    
    async def _initialize_session(self) -> None:
        """Initialize session with configuration."""
        # Создаем событие session.update в правильном формате для OpenAI
        session_event = {
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "instructions": get_system_instructions(),
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 200
                },
                "tools": [tool.model_dump(exclude_unset=True) for tool in get_tools()],
                "tool_choice": "auto",
                "temperature": settings.OPENAI_TEMPERATURE,
                "max_response_output_tokens": settings.MAX_RESPONSE_LENGTH
            }
        }
        
        await self._send_event(session_event)
        logger.info("Session initialized with tools and instructions")
        
        # Log detailed session configuration for debugging
        session_config = session_event.get("session", {})
        logger.info(f"🔧 Session configuration details:")
        logger.info(f"  Temperature: {session_config.get('temperature')}")
        logger.info(f"  Max tokens: {session_config.get('max_response_output_tokens')}")
        logger.info(f"  Modalities: {session_config.get('modalities')}")
        logger.info(f"  Tools count: {len(session_config.get('tools', []))}")
        
        # Log full instructions (system prompt)
        instructions = session_config.get('instructions', '')
        logger.info(f"📝 System instructions (length: {len(instructions)} chars):")
        logger.info(f"Instructions: {instructions}")
    
    async def _send_event(self, event: Any) -> None:
        """Send event to WebSocket."""
        if not self.websocket or self.websocket.closed:
            raise ConnectionError("WebSocket not connected")
        
        # Если это Pydantic модель, конвертируем в dict
        if hasattr(event, 'dict'):
            event_data = event.dict(exclude_unset=True, by_alias=True)
        else:
            event_data = event
            
        # Проверяем, что есть обязательное поле type
        if 'type' not in event_data:
            if hasattr(event, 'type'):
                event_data['type'] = event.type
            else:
                logger.error(f"Event missing 'type' field: {event_data}")
                raise ValueError("Event must have 'type' field")
            
        json_data = json.dumps(event_data, ensure_ascii=False)
        await self.websocket.send(json_data)
        
        event_type = event_data.get('type', 'unknown')
        logger.debug(f"Sent event: {event_type}")
        
        # For session.update, log more details
        if event_type == "session.update":
            logger.debug(f"Full session.update data: {json_data}")
        else:
            logger.debug(f"Event data: {json_data[:300]}...")
    
    async def _listen_events(self) -> None:
        """Listen for incoming WebSocket events."""
        logger.info("🎧 Started listening for WebSocket events")
        
        try:
            async for message in self.websocket:
                if not self.is_connected:
                    logger.debug("Ignoring message - client not connected")
                    break
                    
                try:
                    event_data = json.loads(message)
                    event_type = event_data.get("type", "unknown")

                    await self._handle_event(event_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse event JSON: {e}")
                    logger.debug(f"Raw message: {message[:200]}...")
                except Exception as e:
                    logger.error(f"Error handling event: {e}")
                    
        except (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK) as e:
            logger.warning(f"⚠️ WebSocket соединение закрыто: {type(e).__name__}")
            self.is_connected = False
            
            # Always try to reconnect unless explicitly disabled
            if self._should_reconnect:
                logger.info("🔄 Планирую переподключение...")
                await self._trigger_reconnection()
            else:
                logger.info("Переподключение отключено")
                # Mark all active streams as error
                for stream in self.active_streams.values():
                    if stream.state == StreamState.STREAMING:
                        stream.state = StreamState.ERROR
        
        except Exception as e:
            logger.error(f" Unexpected error in event listener: {e}")
            self.is_connected = False
            
            # Try to reconnect on unexpected errors too
            if self._should_reconnect:
                logger.info("🔄 Планирую переподключение после ошибки...")
                await self._trigger_reconnection()
            
        finally:
            logger.info("🛑 Event listener stopped")
    
    async def _handle_event(self, event_data: Dict[str, Any]) -> None:
        """Handle incoming WebSocket event."""
        event_type = event_data.get("type")
        
        if event_type == EventType.RESPONSE_TEXT_DELTA:
            await self._handle_text_delta(event_data)
        
        elif event_type == EventType.RESPONSE_TEXT_DONE:
            await self._handle_text_done(event_data)
        
        elif event_type == EventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA:
            await self._handle_function_call_delta(event_data)
        
        elif event_type == EventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE:
            await self._handle_function_call_done(event_data)
        
        elif event_type == EventType.RESPONSE_DONE:
            await self._handle_response_done(event_data)
        
        elif event_type == "response.created":
            await self._handle_response_created(event_data)
        
        elif event_type == EventType.ERROR:
            await self._handle_error(event_data)
        
        else:
            logger.debug(f"Unhandled event type: {event_type}")
    
    async def _handle_text_delta(self, event_data: Dict[str, Any]) -> None:
        """Handle text delta event."""
        response_id = event_data.get("response_id")
        delta = event_data.get("delta", "")
        
        # Find stream by response_id
        stream = self._find_stream_by_response_id(response_id)
        if not stream:
            logger.warning(f"⚠️ Не найден активный стрим для response.text.delta (response_id: {response_id})")
            return
        
        stream.accumulated_text += delta
        stream.state = StreamState.STREAMING
        
        # Call delta callback if set
        if hasattr(stream, '_delta_callback') and stream._delta_callback:
            try:
                await stream._delta_callback(delta, stream.accumulated_text)
            except Exception as e:
                logger.error(f"Error in delta callback: {e}")
    
    async def _handle_text_done(self, event_data: Dict[str, Any]) -> None:
        """Handle text done event."""
        response_id = event_data.get("response_id")
        final_text = event_data.get("text", "")
        
        stream = self._find_stream_by_response_id(response_id)
        if not stream:
            return
        
        # Проверяем, не завершен ли уже стрим
        if stream.state == StreamState.DONE:
            logger.info(f"Сообщение уже финализировано для пользователя {stream.user_id}, пропускаем")
            return
        
        stream.accumulated_text = final_text
        stream.state = StreamState.DONE
        
        # Call done callback if set
        if hasattr(stream, '_done_callback') and stream._done_callback:
            try:
                logger.info(f"Финализация сообщения для пользователя {stream.user_id}")
                await stream._done_callback(final_text)
            except Exception as e:
                logger.error(f"Error in done callback: {e}")
    
    async def _handle_function_call_delta(self, event_data: Dict[str, Any]) -> None:
        """Handle function call arguments delta."""
        call_id = event_data.get("call_id")
        delta = event_data.get("delta", "")
        
        if call_id not in self.pending_function_calls:
            self.pending_function_calls[call_id] = {
                "name": "",
                "arguments": "",
                "response_id": event_data.get("response_id")
            }
        
        self.pending_function_calls[call_id]["arguments"] += delta
        logger.debug(f"Function call {call_id} arguments delta: {delta}")
    
    async def _handle_function_call_done(self, event_data: Dict[str, Any]) -> None:
        """Handle function call arguments done."""
        call_id = event_data.get("call_id")
        function_name = event_data.get("name")
        arguments_str = event_data.get("arguments", "{}")
        
        logger.info(f"Function call done: {function_name} with call_id: {call_id}")
        
        try:
            # Parse arguments
            arguments = json.loads(arguments_str)
            
            # Execute function call
            result = await self._execute_function_call(function_name, arguments)
            
            # Send result back
            await self._send_function_result(call_id, result)
            
        except Exception as e:
            logger.error(f"Error executing function call {function_name}: {e}")
            await self._send_function_result(call_id, {
                "error": f"Ошибка выполнения функции: {str(e)}"
            })
        
        # Clean up
        self.pending_function_calls.pop(call_id, None)
    
    async def _execute_function_call(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute YCLIENTS function call."""
        logger.info(f"Executing function: {function_name} with args: {arguments}")
        
        # Map function names to adapter methods
        function_mapping = {
            "yclients_list_services": self.yclients_adapter.list_services,
            "yclients_search_slots": self.yclients_adapter.search_slots,
            "yclients_create_appointment": self.yclients_adapter.yclients_create_appointment,
            "yclients_list_doctors": self.yclients_adapter.list_doctors,
            "get_user_info": self.yclients_adapter.get_user_info,
            "register_user": self.yclients_adapter.register_user,
            "book_appointment_with_profile": self.yclients_adapter.book_appointment_with_profile,
            "sync_user_profile": self.yclients_adapter.sync_user_profile
        }
        
        if function_name not in function_mapping:
            raise ValueError(f"Unknown function: {function_name}")
        
        func = function_mapping[function_name]
        
        # Для функций, которые работают с пользователем, автоматически добавляем telegram_id из контекста
        user_context_functions = {
            "get_user_info", "register_user", "book_appointment_with_profile", 
            "sync_user_profile"
        }
        
        if function_name in user_context_functions:
            # Если telegram_id не передан, используем user_id из контекста клиента
            if "telegram_id" not in arguments or arguments.get("telegram_id") is None:
                arguments["telegram_id"] = self.user_id
        
        try:
            result = await func(**arguments)
            return {"success": True, "data": result}
        
        except Exception as e:
            logger.error(f"Function {function_name} failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_function_result(self, call_id: str, result: Dict[str, Any]) -> None:
        """Send function call result back to the API."""
        # Create function call output item в правильном формате
        event = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result, ensure_ascii=False)
            }
        }
        
        await self._send_event(event)
        logger.info(f"📤 Sent function result for call_id: {call_id}")
        
        # Небольшая задержка для обработки
        await asyncio.sleep(0.2)
        
        # Проверяем, есть ли активный стрим для этого пользователя
        active_stream = None
        for user_id, stream in self.active_streams.items():
            if stream.state not in [StreamState.DONE, StreamState.ERROR, StreamState.CANCELLED]:
                active_stream = stream
                break
        
        if active_stream:
            # ВАЖНО: После отправки результата функции запрашиваем продолжение генерации
            # Добавляем дополнительные параметры для стабильности
            response_event = {
                "type": "response.create",
                "response": {
                    "modalities": ["text"],
                    "temperature": 1.1,
                    "max_output_tokens": 1500
                }
            }
            await self._send_event(response_event)
            logger.info(f"🔄 Requested text generation after function call {call_id}")
        else:
            logger.warning(f"⚠️ No active stream found after function call {call_id}, skipping response.create")
    
    async def _handle_response_done(self, event_data: Dict[str, Any]) -> None:
        """Handle response done event."""
        response_id = event_data.get("response", {}).get("id")
        
        stream = self._find_stream_by_response_id(response_id)
        if stream and stream.state == StreamState.STREAMING:
            stream.state = StreamState.DONE
    
    async def _handle_response_created(self, event_data: Dict[str, Any]) -> None:
        """Handle response created event."""
        response = event_data.get("response", {})
        temperature = response.get("temperature")
        response_id = response.get("id")
        
        logger.info(f"🔍 Детали события response.created: {event_data}")
        logger.info(f"🌡️ Response created with temperature: {temperature}, response_id: {response_id}")
        
        # Find and update stream with response_id
        stream_updated = False
        for user_id, stream in self.active_streams.items():
            # Связываем с любым активным стримом, который еще не завершен
            if stream.state not in [StreamState.DONE, StreamState.ERROR, StreamState.CANCELLED]:
                # Обновляем response_id (может быть новый после function call)
                old_response_id = getattr(stream, 'response_id', None)
                stream.response_id = response_id
                
                # Добавляем таймстамп создания response для отслеживания зависших ответов
                stream.response_created_at = datetime.utcnow()
                stream_updated = True
                
                if old_response_id != response_id:
                    logger.info(f"🔄 Обновили response_id для пользователя {user_id}: {old_response_id} → {response_id}")
                else:
                    logger.info(f"🔗 Связали OpenAI response_id {response_id} с пользователем {user_id}")
                break
        
        if not stream_updated:
            logger.warning(f"⚠️ Не найден активный стрим для response_id {response_id}")
            
        # Запускаем задачу мониторинга зависшего response
        asyncio.create_task(self._monitor_response_timeout(response_id))
    
    async def _handle_error(self, event_data: Dict[str, Any]) -> None:
        """Handle error event."""
        error = event_data.get("error", {})
        error_message = error.get("message", "Unknown error")
        logger.error(f"Realtime API error: {error_message}")
        
        # Mark all active streams as error
        for stream in self.active_streams.values():
            if stream.state == StreamState.STREAMING:
                stream.state = StreamState.ERROR
                if hasattr(stream, '_error_callback') and stream._error_callback:
                    try:
                        await stream._error_callback(Exception(error_message))
                    except Exception as e:
                        logger.error(f"Error in error callback: {e}")
    
    def _find_stream_by_response_id(self, response_id: str) -> Optional[StreamController]:
        """Find active stream by response ID."""
        for stream in self.active_streams.values():
            if stream.response_id == response_id:
                return stream
        
        # Если не нашли точное совпадение, ищем активный стрим без response_id
        # (это может быть новый стрим, который еще не получил response_id)
        for stream in self.active_streams.values():
            if (stream.response_id is None and 
                stream.state in [StreamState.IDLE, StreamState.STREAMING]):
                # Автоматически привязываем response_id к этому стриму
                stream.response_id = response_id
                logger.info(f"🔗 Автоматически связали response_id {response_id} со стримом пользователя {stream.user_id}")
                return stream
        
        return None
    
    async def _monitor_response_timeout(self, response_id: str) -> None:
        """Monitor response for timeout and cancel if hanging."""
        # Ждем 20 секунд - если за это время нет никакого ответа, отменяем
        await asyncio.sleep(20)
        
        # Ищем стрим по response_id
        stream = self._find_stream_by_response_id(response_id)
        if not stream:
            return
            
        # Проверяем, не получили ли мы уже какой-то текст
        if stream.accumulated_text.strip():
            logger.debug(f"Response {response_id} уже получил текст, мониторинг не нужен")
            return
            
        # Проверяем, не завершен ли уже стрим
        if stream.state in [StreamState.DONE, StreamState.ERROR, StreamState.CANCELLED]:
            return
            
        # Проверяем таймстамп создания response
        if hasattr(stream, 'response_created_at'):
            time_elapsed = (datetime.utcnow() - stream.response_created_at).total_seconds()
            if time_elapsed > 20:
                logger.warning(f"⏰ Response {response_id} завис более 20 секунд без ответа, отменяем")
                
                try:
                    # Отменяем зависший response
                    cancel_event = {"type": "response.cancel"}
                    await self._send_event(cancel_event)
                    logger.info(f"❌ Отменен зависший response {response_id}")
                    
                    # Ждем немного и пробуем создать новый
                    await asyncio.sleep(1)
                    
                    # Создаем новый response только если стрим все еще активен
                    if stream.state not in [StreamState.DONE, StreamState.ERROR, StreamState.CANCELLED]:
                        response_event = {
                            "type": "response.create",
                            "response": {
                                "modalities": ["text"],
                                "temperature": 1.0,  # Немного снижаем температуру для стабильности
                                "max_output_tokens": 1500
                            }
                        }
                        await self._send_event(response_event)
                        logger.info(f"🔄 Создан новый response взамен зависшего {response_id}")
                        
                except Exception as e:
                    logger.error(f"Ошибка при отмене зависшего response {response_id}: {e}")
    
    async def ensure_connected(self) -> None:
        """Ensure WebSocket is connected, reconnect if needed."""
        if not self.is_connected or not self.websocket or self.websocket.closed:
            logger.info("Connection lost, attempting to reconnect...")
            await self.connect()
    
    async def send_user_message(
        self,
        user_id: int,
        text: str,
        message_id: Optional[int] = None
    ) -> StreamController:
        """Send user message and return stream controller."""
        # Ensure we're connected
        await self.ensure_connected()
        
        # Cancel any existing stream for this user
        if user_id in self.active_streams:
            await self.cancel_stream(user_id)
        
        # Create stream controller
        stream = StreamController(
            user_id=user_id,
            message_id=message_id,
            state=StreamState.IDLE
        )
        self.active_streams[user_id] = stream
        
        try:
            # Create conversation item в правильном формате
            create_event = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": text
                        }
                    ]
                }
            }
            await self._send_event(create_event)
            
            # Create response
            response_event = {
                "type": "response.create"
            }
            await self._send_event(response_event)
            
            logger.info(f"Sent user message from user {user_id}: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to send user message: {e}")
            stream.state = StreamState.ERROR
            raise
        
        return stream
    
    async def cancel_stream(self, user_id: int) -> None:
        """Cancel active stream for user."""
        stream = self.active_streams.get(user_id)
        if not stream:
            logger.debug(f"No active stream found for user {user_id}")
            return
            
        # Проверяем состояние стрима
        if stream.state in [StreamState.DONE, StreamState.ERROR, StreamState.CANCELLED]:
            logger.info(f"🗑️ Очищен стрим для пользователя {user_id}")
            self.active_streams.pop(user_id, None)
            return
        
        try:
            # Отправляем cancel только если стрим активен
            if stream.state in [StreamState.STREAMING, StreamState.IDLE]:
                # Проверяем, есть ли активный response для отмены
                if hasattr(stream, 'response_id') and stream.response_id:
                    logger.info(f"📤 Отправлен cancel для response_id: {stream.response_id}")
                    cancel_event = {
                        "type": "response.cancel"
                    }
                    await self._send_event(cancel_event)
                    
                    # Ждем немного, чтобы отмена прошла
                    await asyncio.sleep(0.1)
                else:
                    logger.debug(f"Нет активного response для отмены у пользователя {user_id}")
            
            stream.state = StreamState.CANCELLED
            
            # Очищаем response_id для предотвращения дальнейших попыток
            if hasattr(stream, 'response_id'):
                stream.response_id = None
                
            logger.info(f"🗑️ Очищен стрим для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to cancel stream: {e}")
            # Не прерываем выполнение, все равно очищаем стрим
        
        finally:
            # Remove from active streams
            self.active_streams.pop(user_id, None)
    
    def set_stream_callbacks(
        self,
        user_id: int,
        on_delta: Optional[Callable[[str, str], Any]] = None,
        on_done: Optional[Callable[[str], Any]] = None,
        on_error: Optional[Callable[[Exception], Any]] = None,
    ) -> None:
        """Set callbacks for stream events."""
        stream = self.active_streams.get(user_id)
        if not stream:
            return
        
        if on_delta:
            stream._delta_callback = on_delta
        if on_done:
            stream._done_callback = on_done
        if on_error:
            stream._error_callback = on_error
    
    def get_stream_state(self, user_id: int) -> Optional[StreamState]:
        """Get current stream state for user."""
        stream = self.active_streams.get(user_id)
        return stream.state if stream else None
    
    def cleanup_finished_streams(self) -> None:
        """Clean up finished streams."""
        finished_users = []
        for user_id, stream in self.active_streams.items():
            if stream.state in [StreamState.DONE, StreamState.ERROR, StreamState.CANCELLED]:
                # Keep stream for a short while to allow final callbacks
                if (datetime.utcnow() - stream.created_at).seconds > 60:
                    finished_users.append(user_id)
        
        for user_id in finished_users:
            self.active_streams.pop(user_id, None)
            logger.debug(f"Cleaned up finished stream for user {user_id}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "is_connected": self.is_connected,
            "reconnect_attempts": self._reconnect_attempts,
            "max_reconnect_attempts": self._max_reconnect_attempts,
            "should_reconnect": self._should_reconnect,
            "active_streams": len(self.active_streams),
            "pending_function_calls": len(self.pending_function_calls),
            "last_pong_time": self._last_pong_time.isoformat() if self._last_pong_time else None,
            "websocket_closed": not self.websocket or self.websocket.closed,
            "consecutive_failures": self._consecutive_failures,
            "circuit_breaker_open": self._circuit_breaker_open,
            "circuit_breaker_open_time": self._circuit_breaker_open_time.isoformat() if self._circuit_breaker_open_time else None,
            "last_reconnect_time": self._last_reconnect_time.isoformat() if self._last_reconnect_time else None,
            "reconnecting": self._reconnecting,
        }


class RealtimeClientManager:
    """Менеджер отдельных OpenAI клиентов для каждого пользователя."""
    
    def __init__(self, yclients_adapter: YClientsAdapter):
        self.yclients_adapter = yclients_adapter
        self.user_clients: Dict[int, OpenAIRealtimeClient] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
        
        logger.info("🔧 Initialized RealtimeClientManager for per-user sessions")
    
    def _start_cleanup_task(self):
        """Запускает фоновую задачу очистки неактивных клиентов."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_inactive_clients())
    
    async def _cleanup_inactive_clients(self):
        """Очищает неактивных клиентов старше 1 часа."""
        while True:
            try:
                current_time = datetime.utcnow()
                inactive_users = []
                
                for user_id, client in self.user_clients.items():
                    # Удаляем клиентов неактивных более 1 часа
                    if (current_time - client._created_at).total_seconds() > 3600:
                        # Проверяем, есть ли активные стримы
                        if not client.active_streams:
                            inactive_users.append(user_id)
                            logger.info(f"🧹 Marking user {user_id} client for cleanup (inactive for 1+ hour)")
                
                # Очищаем неактивных клиентов
                for user_id in inactive_users:
                    try:
                        client = self.user_clients.pop(user_id, None)
                        if client:
                            await client.disconnect()
                            logger.info(f"🗑️ Cleaned up inactive client for user {user_id}")
                    except Exception as e:
                        logger.error(f"Error cleaning up client for user {user_id}: {e}")
                
                # Спим 30 минут до следующей проверки
                await asyncio.sleep(1800)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(300)  # При ошибке ждем 5 минут
    
    async def get_client_for_user(self, user_id: int) -> OpenAIRealtimeClient:
        """Получает или создает клиент для конкретного пользователя."""
        if user_id not in self.user_clients:
            # Создаем новый клиент для пользователя
            client = OpenAIRealtimeClient(self.yclients_adapter, user_id)
            await client.connect()
            self.user_clients[user_id] = client
            logger.info(f"✅ Created and connected new client for user {user_id}")
        else:
            client = self.user_clients[user_id]
            # Проверяем соединение
            if not client.is_connected:
                logger.info(f"🔄 Reconnecting client for user {user_id}")
                await client.connect()
        
        return self.user_clients[user_id]
    
    async def remove_client_for_user(self, user_id: int) -> None:
        """Удаляет клиент для пользователя."""
        if user_id in self.user_clients:
            client = self.user_clients.pop(user_id)
            await client.disconnect()
            logger.info(f"🗑️ Removed client for user {user_id}")
    
    async def cleanup_all(self) -> None:
        """Очищает всех клиентов."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        for user_id, client in self.user_clients.items():
            try:
                await client.disconnect()
                logger.info(f"🗑️ Disconnected client for user {user_id}")
            except Exception as e:
                logger.error(f"Error disconnecting client for user {user_id}: {e}")
        
        self.user_clients.clear()
        logger.info("🧹 All clients cleaned up")
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику менеджера."""
        connected_clients = sum(1 for client in self.user_clients.values() if client.is_connected)
        active_streams = sum(len(client.active_streams) for client in self.user_clients.values())
        
        return {
            "total_clients": len(self.user_clients),
            "connected_clients": connected_clients,
            "active_streams": active_streams,
            "users": list(self.user_clients.keys())
        }


# Global client manager instance
_client_manager: Optional[RealtimeClientManager] = None


async def get_realtime_client(yclients_adapter: YClientsAdapter, user_id: int = 0) -> OpenAIRealtimeClient:
    """Get or create Realtime client for specific user."""
    global _client_manager
    
    if _client_manager is None:
        _client_manager = RealtimeClientManager(yclients_adapter)
    
    return await _client_manager.get_client_for_user(user_id)


async def cleanup_realtime_client() -> None:
    """Cleanup all Realtime clients."""
    global _client_manager
    
    if _client_manager:
        logger.info("Cleaning up all Realtime clients...")
        await _client_manager.cleanup_all()
        _client_manager = None


async def restart_realtime_client(yclients_adapter: YClientsAdapter, user_id: int = 0) -> OpenAIRealtimeClient:
    """Restart Realtime client with fresh settings."""
    logger.info(f"🔄 Restarting Realtime client for user {user_id} with new settings...")
    
    global _client_manager
    if _client_manager:
        await _client_manager.remove_client_for_user(user_id)
    
    # Create new client with current settings
    return await get_realtime_client(yclients_adapter, user_id)
