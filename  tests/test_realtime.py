#!/usr/bin/env python3
"""
Тестовая версия бота с OpenAI Realtime API для отладки WebSocket соединения.
"""

import asyncio
import json
import logging
import os
from dotenv import load_dotenv
import websockets
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

# Загружаем .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()

class SimpleRealtimeClient:
    """Упрощенный клиент для тестирования WebSocket соединения с OpenAI."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.ws_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"
        self.websocket = None
        self.is_connected = False
        
    async def connect(self):
        """Подключение к OpenAI Realtime API."""
        try:
            logger.info("🔌 Подключаемся к OpenAI Realtime API...")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            self.websocket = await websockets.connect(
                self.ws_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            
            self.is_connected = True
            logger.info("✅ Подключение к OpenAI Realtime API успешно!")
            
            # Инициализируем сессию
            await self.initialize_session()
            
            # Запускаем прослушивание событий
            asyncio.create_task(self.listen_events())
            
        except Exception as e:
            logger.error(f" Ошибка подключения к OpenAI: {e}")
            self.is_connected = False
            raise
    
    async def initialize_session(self):
        """Инициализация сессии."""
        session_event = {
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "instructions": "Ты - помощник стоматологической клиники. Отвечай кратко и по делу.",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 200
                },
                "tools": [],
                "tool_choice": "auto",
                "temperature": 0.8
            }
        }
        
        await self.send_event(session_event)
        logger.info("📋 Сессия инициализирована")
    
    async def send_event(self, event):
        """Отправка события в WebSocket."""
        if not self.websocket or self.websocket.closed:
            raise ConnectionError("WebSocket не подключен")
        
        json_data = json.dumps(event, ensure_ascii=False)
        await self.websocket.send(json_data)
        logger.debug(f"📤 Отправлено: {event.get('type', 'unknown')}")
        logger.debug(f"📤 Данные: {json_data[:200]}...")
    
    async def listen_events(self):
        """Прослушивание входящих событий."""
        try:
            async for message in self.websocket:
                try:
                    event_data = json.loads(message)
                    await self.handle_event(event_data)
                except json.JSONDecodeError as e:
                    logger.error(f" Ошибка парсинга JSON: {e}")
                except Exception as e:
                    logger.error(f" Ошибка обработки события: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("⚠️ WebSocket соединение закрыто")
            self.is_connected = False
        
        except Exception as e:
            logger.error(f" Неожиданная ошибка в прослушивании: {e}")
    
    async def handle_event(self, event_data):
        """Обработка входящих событий."""
        event_type = event_data.get("type")
        logger.info(f"📥 Получено событие: {event_type}")
        
        if event_type == "session.updated":
            logger.info("✅ Сессия обновлена")
        
        elif event_type == "response.text.delta":
            delta = event_data.get("delta", "")
            logger.info(f"📝 Текст дельта: {delta}")
        
        elif event_type == "response.text.done":
            text = event_data.get("text", "")
            logger.info(f"Текст завершен: {text}")
        
        elif event_type == "error":
            error = event_data.get("error", {})
            logger.error(f" Ошибка от OpenAI: {error}")
        
        else:
            logger.debug(f"🔍 Неизвестное событие: {event_type}")
    
    async def send_user_message(self, text):
        """Отправка сообщения пользователя."""
        # Создаем элемент беседы
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
        await self.send_event(create_event)
        
        # Создаем ответ
        response_event = {
            "type": "response.create"
        }
        await self.send_event(response_event)
        
        logger.info(f"💬 Отправлено сообщение: {text[:50]}...")

# Глобальный клиент
realtime_client = SimpleRealtimeClient()

@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    """Обработчик /start."""
    await message.answer(
        "🤖 <b>Тестовый бот с OpenAI Realtime API</b>\n\n"
        "Отправьте любое сообщение для тестирования WebSocket соединения с OpenAI.",
        parse_mode="HTML"
    )

@router.message(F.text)
async def text_handler(message: Message) -> None:
    """Обработчик текстовых сообщений."""
    if not realtime_client.is_connected:
        await message.answer(" WebSocket не подключен к OpenAI")
        return
    
    # Отправляем "думаю..."
    thinking_msg = await message.answer("🤔 Отправляю запрос в OpenAI...")
    
    try:
        # Отправляем сообщение в OpenAI
        await realtime_client.send_user_message(message.text)
        
        # Обновляем сообщение
        await thinking_msg.edit_text(
            f"Сообщение отправлено в OpenAI Realtime API!\n\n"
            f"📤 Ваше сообщение: <i>{message.text}</i>\n\n"
            f"📋 Проверьте логи для просмотра ответа от OpenAI.",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        await thinking_msg.edit_text(f" Ошибка: {e}")

async def main():
    """Главная функция."""
    token = os.getenv("TG_BOT_TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        logger.error(" Токен бота не найден!")
        return
    
    if not os.getenv("OPENAI_API_KEY"):
        logger.error(" OpenAI API ключ не найден!")
        return
    
    # Подключаемся к OpenAI
    try:
        await realtime_client.connect()
    except Exception as e:
        logger.error(f" Не удалось подключиться к OpenAI: {e}")
        return
    
    # Создаем бота
    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)
    
    logger.info("🚀 Запускаем тестового бота с OpenAI Realtime API...")
    
    try:
        await dp.start_polling(bot, skip_updates=True)
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")
    finally:
        await bot.session.close()
        if realtime_client.websocket:
            await realtime_client.websocket.close()

if __name__ == "__main__":
    asyncio.run(main())
