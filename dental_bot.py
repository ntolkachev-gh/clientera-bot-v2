#!/usr/bin/env python3
"""
Telegram-бот консультант для стоматологической клиники с OpenAI Realtime API.
"""

import asyncio
import fcntl
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

from dotenv import load_dotenv
import websockets
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
import aiohttp
from aiohttp import web

# Импорт YClients адаптера и realtime клиента
from src.integrations.yclients_adapter import get_yclients_adapter
from src.realtime.client import OpenAIRealtimeClient

# Загружаем .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Настройка фильтрации TLS ошибок в aiohttp
class TLSErrorFilter(logging.Filter):
    """Фильтр для подавления TLS handshake ошибок."""

    def filter(self, record):
        # Игнорируем TLS handshake ошибки
        if "Invalid method encountered" in record.getMessage():
            return False
        if "BadStatusLine" in record.getMessage():
            return False
        return True


# Применяем фильтр к aiohttp логгерам
aiohttp_logger = logging.getLogger('aiohttp.server')
aiohttp_logger.addFilter(TLSErrorFilter())
aiohttp_access_logger = logging.getLogger('aiohttp.access')
aiohttp_access_logger.addFilter(TLSErrorFilter())

# Создаем роутер
router = Router()


class DoctorsCache:
    """Кеш для информации о врачах с TTL 24 часа."""

    def __init__(self, ttl_hours: int = 24):
        self.ttl_seconds = ttl_hours * 3600  # TTL в секундах
        self.cache: Dict[str, Any] = {}  # key -> {"data": data, "timestamp": timestamp}

    def _is_expired(self, timestamp: float) -> bool:
        """Проверяет, истек ли срок действия кеша."""
        return time.time() - timestamp > self.ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Получает данные из кеша, если они не истекли."""
        if key not in self.cache:
            return None

        cache_entry = self.cache[key]
        if self._is_expired(cache_entry["timestamp"]):
            # Удаляем истекшие данные
            del self.cache[key]
            return None

        return cache_entry["data"]

    def set(self, key: str, data: Any) -> None:
        """Сохраняет данные в кеш с текущим временем."""
        self.cache[key] = {
            "data": data,
            "timestamp": time.time()
        }

    def clear(self) -> None:
        """Очищает весь кеш."""
        self.cache.clear()

    def cleanup_expired(self) -> int:
        """Удаляет все истекшие записи из кеша. Возвращает количество удаленных записей."""
        current_time = time.time()
        expired_keys = []

        for key, cache_entry in self.cache.items():
            if self._is_expired(cache_entry["timestamp"]):
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кеша."""
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0

        for cache_entry in self.cache.values():
            if self._is_expired(cache_entry["timestamp"]):
                expired_entries += 1
            else:
                valid_entries += 1

        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "ttl_hours": self.ttl_seconds / 3600
        }


# Глобальные кеши
doctors_cache = DoctorsCache(ttl_hours=24)
services_cache = DoctorsCache(ttl_hours=1)  # Кеш услуг на 1 час


class AdminServer:
    """HTTP сервер для администрирования бота."""

    def __init__(self, yclients_integration, port=8080):
        self.yclients = yclients_integration
        self.port = port
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """Настройка маршрутов."""

        # Добавляем middleware для обработки TLS ошибок
        @web.middleware
        async def error_middleware(request, handler):
            try:
                return await handler(request)
            except Exception as e:
                # Логируем только серьезные ошибки, игнорируем TLS handshake
                if "Invalid method encountered" not in str(e) and "BadStatusLine" not in str(e):
                    logger.error(f"Ошибка обработки запроса: {e}")
                return web.Response(text="Bad Request", status=400)

        self.app.middlewares.append(error_middleware)

        self.app.router.add_get('/', self.index)
        self.app.router.add_post('/cache/clear', self.clear_cache)
        self.app.router.add_get('/cache/stats', self.cache_stats)
        self.app.router.add_post('/cache/refresh', self.refresh_cache)
        self.app.router.add_get('/health', self.health_check)

    async def index(self, request):
        """Главная страница админки."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>🦷 Админка стоматологического бота</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
                .button { padding: 10px 15px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; }
                .btn-danger { background: #dc3545; color: white; }
                .btn-primary { background: #007bff; color: white; }
                .btn-success { background: #28a745; color: white; }
                .stats { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
                .title { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="title">🦷 Админка стоматологического бота</h1>
                
                <div style="background: #d1ecf1; border: 1px solid #bee5eb; border-radius: 5px; padding: 10px; margin: 15px 0;">
                    <strong>ℹ️ Важно:</strong> Используйте только <code>http://localhost:8080</code> (HTTP, не HTTPS)
                </div>
                
                <h2>📊 Управление кешем</h2>
                <button class="button btn-danger" onclick="clearCache()">🗑️ Очистить все кеши</button>
                <button class="button btn-primary" onclick="refreshCache()">🔄 Обновить кеши</button>
                <button class="button btn-success" onclick="loadStats()">📈 Обновить статистику</button>
                
                <div id="stats"></div>
                
                <h2>🔧 API Endpoints</h2>
                <ul>
                    <li><code>GET /</code> - Эта страница</li>
                    <li><code>POST /cache/clear</code> - Очистить все кеши</li>
                    <li><code>GET /cache/stats</code> - Статистика кешей</li>
                    <li><code>POST /cache/refresh</code> - Обновить кеши</li>
                    <li><code>GET /health</code> - Проверка здоровья</li>
                </ul>
            </div>
            
            <script>
                async function clearCache() {
                    if (confirm('Очистить все кеши?')) {
                        const response = await fetch('/cache/clear', { method: 'POST' });
                        const result = await response.json();
                        alert(result.message);
                        loadStats();
                    }
                }
                
                async function refreshCache() {
                    if (confirm('Обновить кеши?')) {
                        const response = await fetch('/cache/refresh', { method: 'POST' });
                        const result = await response.json();
                        alert(result.message);
                        loadStats();
                    }
                }
                
                async function loadStats() {
                    const response = await fetch('/cache/stats');
                    const stats = await response.json();
                    document.getElementById('stats').innerHTML = 
                        '<div class="stats"><h3>📊 Статистика кешей</h3><pre>' + 
                        JSON.stringify(stats, null, 2) + '</pre></div>';
                }
                
                // Загружаем статистику при загрузке страницы
                loadStats();
                
                // Автообновление каждые 30 секунд
                setInterval(loadStats, 30000);
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

    async def clear_cache(self, request):
        """Очистка всех кешей."""
        try:
            self.yclients.clear_all_cache()
            logger.info("🗑️ Все кеши очищены через админку")
            return web.json_response({
                "success": True,
                "message": "Все кеши успешно очищены"
            })
        except Exception as e:
            logger.error(f" Ошибка очистки кешей через админку: {e}")
            return web.json_response({
                "success": False,
                "message": f"Ошибка очистки кешей: {str(e)}"
            }, status=500)

    async def cache_stats(self, request):
        """Статистика кешей."""
        try:
            stats = self.yclients.get_all_cache_stats()
            return web.json_response({
                "success": True,
                "stats": stats,
                "timestamp": time.time()
            })
        except Exception as e:
            logger.error(f" Ошибка получения статистики кешей: {e}")
            return web.json_response({
                "success": False,
                "message": f"Ошибка получения статистики: {str(e)}"
            }, status=500)

    async def refresh_cache(self, request):
        """Обновление кешей."""
        try:
            # Помечаем кеши для обновления
            self.yclients.refresh_doctors_cache()
            self.yclients.refresh_services_cache()

            logger.info("🔄 Кеши помечены для обновления через админку")
            return web.json_response({
                "success": True,
                "message": "Кеши помечены для обновления. Следующие запросы загрузят свежие данные."
            })
        except Exception as e:
            logger.error(f" Ошибка обновления кешей через админку: {e}")
            return web.json_response({
                "success": False,
                "message": f"Ошибка обновления кешей: {str(e)}"
            }, status=500)

    async def health_check(self, request):
        """Проверка здоровья сервера."""
        return web.json_response({
            "status": "healthy",
            "timestamp": time.time(),
            "uptime": time.time() - start_time if 'start_time' in globals() else 0
        })

    async def start(self):
        """Запуск HTTP сервера."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        logger.info(f"🌐 Админка запущена на http://localhost:{self.port}")
        return runner


# Глобальная переменная для времени запуска
start_time = time.time()


class DentalRealtimeClient:
    """Клиент OpenAI Realtime API для стоматологической клиники."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.ws_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"
        self.websocket = None
        self.is_connected = False
        self.active_streams: Dict[int, Dict] = {}  # user_id -> stream_data
        self.response_to_user: Dict[str, int] = {}  # response_id -> user_id
        self.completed_responses: set = set()  # response_id для завершенных ответов

        # Счетчики для подсчета стоимости
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

        # Инициализируем YClients адаптер
        self.yclients = get_yclients_adapter()

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Расчет стоимости токенов для GPT-4o Realtime API.
        Цены на декабрь 2024:
        - Input tokens: $2.50 / 1M tokens
        - Output tokens: $10.00 / 1M tokens
        """
        input_cost = (input_tokens / 1_000_000) * 2.50
        output_cost = (output_tokens / 1_000_000) * 10.00
        return input_cost + output_cost

    def update_token_usage(self, usage_data: dict):
        """Обновляет счетчики токенов и стоимости."""
        if not usage_data:
            return

        input_tokens = usage_data.get('input_tokens', 0)
        output_tokens = usage_data.get('output_tokens', 0)

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        session_cost = self.calculate_cost(input_tokens, output_tokens)
        self.total_cost += session_cost

        logger.info(
            f"💰 Токены: {input_tokens} вход + {output_tokens} выход = ${session_cost:.4f} (всего: ${total_cost:.4f})")


# Удален дублированный код старого класса DentalRealtimeClient


@router.message(CommandStart())



class DentalRealtimeClient:
    """Клиент OpenAI Realtime API для стоматологической клиники."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.ws_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"
        self.websocket = None
        self.is_connected = False
        self.active_streams: Dict[int, Dict] = {}  # user_id -> stream_data
        self.response_to_user: Dict[str, int] = {}  # response_id -> user_id
        self.completed_responses: set = set()  # response_id для завершенных ответов

        # Счетчики для подсчета стоимости
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

        # Инициализируем YClients адаптер
        self.yclients = get_yclients_adapter()

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Расчет стоимости токенов для GPT-4o Realtime API.
        Цены на декабрь 2024:
        - Input tokens: $2.50 / 1M tokens
        - Output tokens: $10.00 / 1M tokens
        """
        input_cost = (input_tokens / 1_000_000) * 2.50
        output_cost = (output_tokens / 1_000_000) * 10.00
        return input_cost + output_cost

    def update_token_usage(self, usage_data: dict):
        """Обновляет счетчики токенов и стоимости."""
        if not usage_data:
            return

        input_tokens = usage_data.get('input_tokens', 0)
        output_tokens = usage_data.get('output_tokens', 0)

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        session_cost = self.calculate_cost(input_tokens, output_tokens)
        self.total_cost += session_cost

        logger.info(
            f"💰 Токены: {input_tokens} вход + {output_tokens} выход = ${session_cost:.4f} (всего: ${self.total_cost:.4f})")

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
        """Инициализация сессии с инструментами стоматологической клиники."""

        # Определяем инструменты для работы с клиникой в правильном формате OpenAI Realtime API
        tools = [
            {
                "type": "function",
                "name": "get_services",
                "description": "Получить список услуг стоматологической клиники с ценами",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Категория услуг",
                            "enum": ["терапия", "хирургия", "ортопедия", "ортодонтия", "имплантация", "профгигиена",
                                     "все"]
                        }
                    }
                }
            },
            {
                "type": "function",
                "name": "get_doctors",
                "description": "Получить список врачей клиники",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "specialization": {
                            "type": "string",
                            "description": "Специализация врача",
                            "enum": ["терапевт", "хирург", "ортопед", "ортодонт", "имплантолог", "гигиенист", "все"]
                        }
                    }
                }
            },
            {
                "type": "function",
                "name": "search_appointments",
                "description": "Найти свободные слоты для записи",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Название услуги"
                        },
                        "doctor": {
                            "type": "string",
                            "description": "Имя врача (опционально)"
                        },
                        "date": {
                            "type": "string",
                            "description": "Предпочитаемая дата в формате YYYY-MM-DD"
                        }
                    },
                    "required": ["service"]
                }
            },
            {
                "type": "function",
                "name": "book_appointment",
                "description": "Записать пациента на прием",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_name": {
                            "type": "string",
                            "description": "Имя пациента"
                        },
                        "phone": {
                            "type": "string",
                            "description": "Телефон пациента"
                        },
                        "service": {
                            "type": "string",
                            "description": "Услуга"
                        },
                        "doctor": {
                            "type": "string",
                            "description": "Врач"
                        },
                        "datetime": {
                            "type": "string",
                            "description": "Дата и время записи"
                        }
                    },
                    "required": ["patient_name", "phone", "service", "doctor", "datetime"]
                }
            }
        ]

        session_event = {
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "instructions": """Ты - профессиональный консультант стоматологической клиники "Белые зубы". 

ТВОЯ РОЛЬ:
- Помогаешь пациентам с записью на прием
- Консультируешь по услугам и ценам
- Отвечаешь на вопросы о лечении
- Всегда вежлив и профессионален

ВАЖНЫЕ ПРАВИЛА:
1. Для получения информации о услугах, врачах и записи ВСЕГДА используй доступные функции
2. НИКОГДА не выдумывай цены, расписание или информацию о врачах
3. Если функция недоступна, честно сообщи об этом
4. Будь краток и структурирован - используй списки и эмодзи
5. При записи обязательно уточни имя и телефон пациента
6. Предлагай конкретные действия: "Записаться", "Посмотреть цены", "Выбрать врача"

СТИЛЬ ОБЩЕНИЯ:
- Дружелюбный, но профессиональный
- Используй эмодзи: 🦷 😊 📅 💰 👨‍⚕️ 📋
- Обращайся на "Вы"
- Завершай сообщения вопросом или предложением действия

ПРИМЕРЫ ХОРОШИХ ОТВЕТОВ:
"Покажу актуальные цены на лечение:
🦷 Лечение кариеса: от 3500₽
🧽 Профессиональная чистка: 4500₽  
💎 Установка пломбы: от 2800₽

📅 Хотите записаться на прием к врачу?"

"Нашел свободные слоты:
👨‍⚕️ Завтра 10:00 - Иванов И.И. (терапевт)
👩‍⚕️ Завтра 14:30 - Петрова А.С. (терапевт)  

Какое время Вам удобно?"

Отвечай кратко (до 1200 символов) и всегда предлагай следующий шаг.""",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 200
                },
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0.7,
                "max_response_output_tokens": 1000
            }
        }

        await self.send_event(session_event)
        logger.info("📋 Сессия инициализирована с инструментами стоматологической клиники")

    async def send_event(self, event):
        """Отправка события в WebSocket."""
        # Проверяем соединение и переподключаемся при необходимости
        if not self.websocket or self.websocket.closed or not self.is_connected:
            logger.warning("⚠️ WebSocket не подключен, пытаемся переподключиться...")
            try:
                await self.connect()
            except Exception as e:
                logger.error(f" Не удалось переподключиться: {e}")
                raise ConnectionError("WebSocket не подключен")

        json_data = json.dumps(event, ensure_ascii=False)
        await self.websocket.send(json_data)
        logger.debug(f"📤 Отправлено: {event.get('type', 'unknown')}")

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
            # Пытаемся переподключиться через 5 секунд
            await asyncio.sleep(5)
            try:
                logger.info("🔄 Пытаемся переподключиться...")
                await self.connect()
            except Exception as reconnect_error:
                logger.error(f" Не удалось переподключиться: {reconnect_error}")

        except Exception as e:
            logger.error(f" Неожиданная ошибка в прослушивании: {e}")
            self.is_connected = False

    async def handle_event(self, event_data):
        """Обработка входящих событий."""
        event_type = event_data.get("type")

        # Добавляем детальную диагностику для проблемных событий
        if event_type in ["response.created", "response.done", "error"]:
            logger.info(f"🔍 Детали события {event_type}: {event_data}")

        if event_type == "session.updated":
            logger.info("✅ Сессия обновлена")

        elif event_type == "response.created":
            # Сохраняем связь между OpenAI response_id и user_id
            openai_response_id = event_data.get("response", {}).get("id")
            if openai_response_id and self.active_streams:
                # Находим последний активный стрим (который только что отправил запрос)
                for user_id, stream_data in self.active_streams.items():
                    if not stream_data.get("completed", False):
                        # Сохраняем OpenAI response_id для этого пользователя
                        self.response_to_user[openai_response_id] = user_id
                        logger.info(f"🔗 Связали OpenAI response_id {openai_response_id} с пользователем {user_id}")
                        break

        elif event_type == "response.text.delta":
            # Обрабатываем стриминг текста
            delta = event_data.get("delta", "")
            response_id = event_data.get("response_id")

            # Находим активный стрим
            user_id = None
            if response_id and response_id in self.response_to_user:
                user_id = self.response_to_user[response_id]
            elif not response_id and self.active_streams:
                # Если response_id отсутствует, берем первый активный стрим
                user_id = next(iter(self.active_streams.keys()))
                logger.debug(f"⚠️ response.text.delta без response_id, используем стрим пользователя {user_id}")

            if user_id and user_id in self.active_streams:
                stream_data = self.active_streams[user_id]

                stream_data["accumulated_text"] += delta
                logger.debug(f"📝 Накопленный текст: {stream_data['accumulated_text'][:100]}...")

                # Обновляем сообщение в реальном времени
                current_time = asyncio.get_event_loop().time()
                last_update = stream_data.get("last_update", 0)

                # Разумный throttling для избежания Telegram rate limits
                should_update = (
                        current_time - last_update > 0.3 or  # Обновляем максимум каждые 300ms
                        len(delta) > 10 or  # Или если дельта больше 10 символов
                        delta.endswith(('.', '!', '?', '\n'))
                # Или если завершается предложение/абзац (убираем пробелы)
                )

                if should_update:
                    stream_data["last_update"] = current_time
                    if hasattr(self, 'update_message') and self.update_message:
                        logger.debug(f"🔄 Обновляем сообщение в реальном времени для пользователя {user_id}")
                        asyncio.create_task(self.update_message(user_id, stream_data["accumulated_text"]))
                    else:
                        logger.warning("⚠️ update_message коллбек не установлен")
            else:
                logger.warning(f"⚠️ Не найден активный стрим для response.text.delta (response_id: {response_id})")

        elif event_type == "response.text.done":
            # Завершение текста
            text = event_data.get("text", "")
            response_id = event_data.get("response_id")

            logger.info(f"Текст завершен: {text}... для response_id: {response_id}")

            # Помечаем response как завершенный
            if response_id:
                self.completed_responses.add(response_id)

                # Берем соответствующий стрим
                if response_id in self.response_to_user:
                    user_id = self.response_to_user[response_id]
                    if user_id in self.active_streams:
                        stream_data = self.active_streams[user_id]
                        stream_data["accumulated_text"] = text
                        stream_data["completed"] = True

                        # Принудительно обновляем сообщение перед финализацией
                        # чтобы показать весь накопленный текст
                        if hasattr(self, 'update_message') and self.update_message:
                            logger.info(f"🔄 Принудительное обновление перед финализацией для пользователя {user_id}")
                            asyncio.create_task(self.update_message(user_id, text))
                            # Небольшая задержка перед финализацией
                            await asyncio.sleep(0.1)

                        if hasattr(self, 'finalize_message') and self.finalize_message:
                            asyncio.create_task(self.finalize_message(user_id, text))
                        else:
                            logger.warning("⚠️ finalize_message коллбек не установлен")
            else:
                # Если response_id отсутствует, попробуем найти активный стрим и завершить его
                logger.warning(f"⚠️ response.text.done без response_id, текст: {text[:50]}...")
                if self.active_streams:
                    # Берем первый (и вероятно единственный) активный стрим
                    user_id = next(iter(self.active_streams.keys()))
                    stream_data = self.active_streams[user_id]
                    stream_response_id = stream_data.get("response_id")

                    if stream_response_id:
                        self.completed_responses.add(stream_response_id)
                        logger.info(f"Помечен как завершенный: {stream_response_id} для пользователя {user_id}")

                    stream_data["accumulated_text"] = text
                    stream_data["completed"] = True
                    if hasattr(self, 'finalize_message') and self.finalize_message:
                        asyncio.create_task(self.finalize_message(user_id, text))
                    else:
                        logger.warning("⚠️ finalize_message коллбек не установлен")

        elif event_type == "response.done":
            # Общее завершение response
            response_id = event_data.get("response_id")
            response_data = event_data.get("response", {})

            # Если response_id отсутствует в event_data, берем из response
            if not response_id:
                response_id = response_data.get("id")

            status = response_data.get("status")
            status_details = response_data.get("status_details", {})

            logger.info(f"🏁 Response завершен: {response_id}, статус: {status}")
            logger.debug(f"🔍 Полные данные response.done: {event_data}")

            # Проверяем, не завершился ли response с ошибкой
            if status == "failed":
                error_info = status_details.get("error", {})
                error_type = error_info.get("type", "unknown")
                error_message = error_info.get("message", "Unknown error")

                logger.error(f" Response завершен с ошибкой: {error_type} - {error_message}")

                # Обрабатываем специфичные ошибки
                if error_type == "insufficient_quota":
                    logger.error("💳 КРИТИЧЕСКАЯ ОШИБКА: Превышена квота OpenAI API!")
                    logger.error("🔧 Решение: Пополните баланс на https://platform.openai.com/usage")

                    # Отправляем сообщение об ошибке всем активным пользователям
                    for user_id, stream_data in self.active_streams.items():
                        if hasattr(self, 'send_quota_error_message'):
                            asyncio.create_task(self.send_quota_error_message(user_id))

                # Помечаем все активные response как завершенные
                for user_id, stream_data in self.active_streams.items():
                    stream_response_id = stream_data.get("response_id")
                    if stream_response_id:
                        self.completed_responses.add(stream_response_id)
                        logger.info(
                            f"Помечен как завершенный (ошибка): {stream_response_id} для пользователя {user_id}")

            else:
                # Обычное завершение response - извлекаем текст ответа
                output = response_data.get("output", [])
                final_text = ""

                # Ищем текст в output
                for item in output:
                    if item.get("type") == "message" and item.get("role") == "assistant":
                        content = item.get("content", [])
                        for content_part in content:
                            if content_part.get("type") == "text":
                                final_text = content_part.get("text", "")
                                break
                        if final_text:
                            break

                logger.info(f"📝 Извлечен финальный текст из response.done: '{final_text[:100]}...'")

                # Обрабатываем информацию о токенах и стоимости
                usage_data = response_data.get("usage")
                if usage_data:
                    self.update_token_usage(usage_data)

                # Обрабатываем завершение для всех активных стримов
                # OpenAI возвращает свой response_id, который не совпадает с нашим внутренним
                # Поэтому обрабатываем все активные стримы
                if self.active_streams and final_text:
                    logger.info(f"🔄 Обрабатываем завершение response для {len(self.active_streams)} активных стримов")

                    for user_id, stream_data in list(self.active_streams.items()):
                        # Помечаем наш внутренний response_id как завершенный
                        internal_response_id = stream_data.get("response_id")
                        if internal_response_id:
                            self.completed_responses.add(internal_response_id)

                        # Также помечаем OpenAI response_id как завершенный
                        if response_id:
                            self.completed_responses.add(response_id)

                        logger.info(
                            f"Помечен как завершенный: {internal_response_id} (OpenAI: {response_id}) для пользователя {user_id}")

                        # Проверяем, не было ли сообщение уже отправлено через response.text.done
                        finalized = stream_data.get("finalized", False)

                        if not finalized:
                            # Небольшая задержка для синхронизации с response.text.done
                            await asyncio.sleep(0.01)
                            finalized = stream_data.get("finalized", False)  # Перепроверяем

                        if not finalized:
                            # Отправляем финальный текст пользователю (fallback если response.text.done не сработал)
                            logger.info(
                                f"📤 Сообщение еще не отправлено, вызываем finalize_message для пользователя {user_id}")
                            stream_data["accumulated_text"] = final_text
                            stream_data["completed"] = True
                            if hasattr(self, 'finalize_message') and self.finalize_message:
                                asyncio.create_task(self.finalize_message(user_id, final_text))
                            else:
                                logger.warning("⚠️ finalize_message коллбек не установлен")
                        else:
                            logger.info(f"Сообщение уже отправлено пользователем {user_id}, только очищаем стрим")

                        # НЕ очищаем стрим - оставляем для продолжения диалога
                        # self.active_streams.pop(user_id, None)

                        # Очищаем связи response_id -> user_id для завершенных ответов
                        if internal_response_id:
                            self.response_to_user.pop(internal_response_id, None)
                        if response_id:
                            self.response_to_user.pop(response_id, None)

                        logger.info(f"🔄 Стрим сохранен для продолжения диалога с пользователем {user_id}")

                elif not final_text:
                    logger.warning("⚠️ Финальный текст пустой, не можем отправить пользователю")
                elif not self.active_streams:
                    logger.warning("⚠️ Нет активных стримов для обработки")

            # Ограничиваем размер set'а, чтобы не рос бесконечно
            if len(self.completed_responses) > 1000:
                # Удаляем старые записи (берем произвольные 100)
                old_responses = list(self.completed_responses)[:100]
                for old_response in old_responses:
                    self.completed_responses.discard(old_response)

        elif event_type == "response.function_call_arguments.done":
            # Вызов функции
            await self.handle_function_call(event_data)

        elif event_type == "error":
            error = event_data.get("error", {})
            logger.error(f" Ошибка от OpenAI: {error}")

    async def handle_function_call(self, event_data):
        """Обработка вызова функций."""
        function_name = event_data.get("name")
        arguments_str = event_data.get("arguments", "{}")
        call_id = event_data.get("call_id")

        logger.info(f"🔧 Вызов функции: {function_name} с call_id: {call_id}")
        logger.info(f"🔧 Аргументы: {arguments_str}")

        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError as e:
            logger.error(f" Ошибка парсинга аргументов: {e}")
            arguments = {}

        # Выполняем функцию
        try:
            if function_name == "get_services":
                result = await self.get_services(arguments.get("category", "все"))
            elif function_name == "get_doctors":
                result = await self.get_doctors(arguments.get("specialization", "все"))
            elif function_name == "search_appointments":
                result = await self.search_appointments(
                    arguments.get("service"),
                    arguments.get("doctor"),
                    arguments.get("date")
                )
            elif function_name == "book_appointment":
                result = await self.book_appointment(
                    patient_name=arguments.get("patient_name"),
                    phone=arguments.get("phone"),
                    service=arguments.get("service"),
                    doctor=arguments.get("doctor"),
                    datetime_str=arguments.get("datetime", arguments.get("datetime_str")),
                    comment=arguments.get("comment", "")
                )
            else:
                result = {"error": f"Неизвестная функция: {function_name}"}

            # Отправляем результат обратно
            await self.send_function_result(call_id, result)
            logger.info(f"Результат функции {function_name} отправлен")

        except Exception as e:
            logger.error(f"Ошибка выполнения функции {function_name}: {e}")
            await self.send_function_result(call_id, {"error": str(e)})

    async def send_function_result(self, call_id, result):
        """Отправка результата функции."""
        # Отправляем результат функции
        function_output_event = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result, ensure_ascii=False)
            }
        }
        await self.send_event(function_output_event)

        # Запрашиваем продолжение генерации ответа
        response_event = {
            "type": "response.create"
        }
        await self.send_event(response_event)
        logger.info(f"📤 Запросили продолжение генерации после function call")

    # Моки функций стоматологической клиники
    async def get_services(self, category="все"):
        """Получить услуги клиники из YClients с кешированием."""
        try:
            # Используем YClients интеграцию с кешированием
            yclients_data = await self.yclients.get_services(category)

            # Преобразуем в формат для GPT
            services = []
            for service in yclients_data.get("services", []):
                price_from = service.get("price_from", 0)
                price_to = service.get("price_to", price_from)

                if price_to > price_from:
                    price_str = f"от {price_from}₽ до {price_to}₽"
                else:
                    price_str = f"{price_from}₽" if price_from > 0 else "по запросу"

                service_info = {
                    "name": service.get("name", "Неизвестная услуга"),
                    "price": price_str,
                    "duration": f"{service.get('duration', 60)} мин"
                }

                # Добавляем описание если есть
                if service.get("description"):
                    service_info["description"] = service.get("description")

                services.append(service_info)

            logger.info(f"📋 Получено {len(services)} услуг через YClients (категория: {category})")
            return {"services": services}

        except Exception as e:
            logger.error(f" Ошибка получения услуг: {e}")
            # В случае ошибки API, возвращаем информативное сообщение
            return {
                "error": True,
                "message": f"Не удалось получить список услуг: {str(e)}",
                "services": []
            }

    async def get_doctors(self, specialization="все"):
        """Получить врачей клиники из YClients."""
        try:
            # Используем YClients интеграцию для получения реальных данных
            yclients_data = await self.yclients.get_doctors(specialization)

            logger.info(f"👨‍⚕️ Получено {len(yclients_data.get('doctors', []))} врачей через YClients API")
            return yclients_data

        except Exception as e:
            logger.error(f" Ошибка получения врачей из YClients: {e}")
            # В случае ошибки API, возвращаем информативное сообщение
            return {
                "error": True,
                "message": f"Не удалось получить список врачей: {str(e)}",
                "doctors": []
            }

    async def search_appointments(self, service, doctor=None, date=None):
        """Найти свободные слоты через YClients."""
        try:
            # Используем YClients интеграцию
            yclients_data = await self.yclients.search_appointments(service, doctor, date)

            # Преобразуем в наш формат
            slots = []
            for appointment in yclients_data.get("appointments", []):
                datetime_str = appointment.get("datetime", "")
                try:
                    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                    slots.append({
                        "date": dt.strftime("%d.%m.%Y"),
                        "time": dt.strftime("%H:%M"),
                        "doctor": appointment.get("doctor", "Врач"),
                        "available": appointment.get("available", True)
                    })
                except:
                    continue

            logger.info(f"📅 Найдено {len(slots)} свободных слотов через YClients")
            return {"service": service, "slots": slots}

        except Exception as e:
            logger.error(f" Ошибка поиска слотов: {e}")
            raise

    async def send_user_message(self, user_id, text, message_id):
        """Отправка сообщения пользователя в OpenAI."""
        try:
            # Проверяем соединение перед отправкой
            if not self.is_connected or not self.websocket or self.websocket.closed:
                logger.warning("⚠️ WebSocket не подключен, пытаемся переподключиться...")
                await self.connect()
            # Переиспользуем существующий стрим или создаем новый
            current_time = asyncio.get_event_loop().time()
            response_id = f"resp_{user_id}_{int(current_time)}"

            if user_id in self.active_streams:
                logger.info(f"🔄 Переиспользуем существующий стрим для пользователя {user_id}")
                # Обновляем существующий стрим
                stream_data = self.active_streams[user_id]
                old_response_id = stream_data.get("response_id")

                # Удаляем старую связь response_id -> user_id
                if old_response_id:
                    self.response_to_user.pop(old_response_id, None)

                # Обновляем стрим с новым response_id
                stream_data.update({
                    "message_id": message_id,
                    "response_id": response_id,
                    "accumulated_text": "",
                    "last_update": current_time,
                    "completed": False,
                    "finalized": False
                })
            else:
                logger.info(f"🆕 Создаем новый стрим для пользователя {user_id}")
                # Создаем новый стрим
                self.active_streams[user_id] = {
                    "message_id": message_id,
                    "response_id": response_id,
                    "accumulated_text": "",
                    "last_update": current_time,
                    "created_at": current_time,
                    "completed": False,
                    "finalized": False
                }

            # Устанавливаем новую связь response_id -> user_id
            self.response_to_user[response_id] = user_id

            logger.info(f"📤 Отправляем сообщение от пользователя {user_id} (response_id: {response_id})")

            # Отправляем сообщение
            create_event = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": text}]
                }
            }
            await self.send_event(create_event)
            logger.debug(f"📤 Отправлено conversation.item.create: {create_event}")

            response_event = {"type": "response.create"}
            await self.send_event(response_event)
            logger.debug(f"📤 Отправлено response.create: {response_event}")

            logger.info(f"Сообщение успешно отправлено для пользователя {user_id}")

        except Exception as e:
            logger.error(f" Ошибка при отправке сообщения для пользователя {user_id}: {e}")
            # Очищаем стрим при ошибке
            if user_id in self.active_streams:
                del self.active_streams[user_id]
            # Очищаем все response_id для этого пользователя
            response_ids_to_remove = [
                rid for rid, uid in self.response_to_user.items()
                if uid == user_id
            ]
            for rid in response_ids_to_remove:
                del self.response_to_user[rid]
            raise

    async def cancel_stream(self, user_id):
        """Отмена активного стрима."""
        if user_id in self.active_streams:
            stream_data = self.active_streams[user_id]
            response_id = stream_data.get("response_id")

            # Проверяем, не завершен ли уже response
            if response_id and response_id not in self.completed_responses:
                # Response еще активен, можно отменить
                try:
                    cancel_event = {"type": "response.cancel"}
                    await self.send_event(cancel_event)
                    logger.info(f"📤 Отправлен cancel для response_id: {response_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при отправке cancel event для пользователя {user_id}: {e}")
            else:
                if response_id:
                    logger.info(f"ℹ️ Response {response_id} уже завершен, отмена не требуется")
                else:
                    logger.warning(f"⚠️ Не найден response_id для пользователя {user_id}")

            # Удаляем стрим
            del self.active_streams[user_id]

            # Удаляем связь response_id -> user_id (безопасно)
            response_ids_to_remove = [
                rid for rid, uid in self.response_to_user.items()
                if uid == user_id
            ]
            for rid in response_ids_to_remove:
                del self.response_to_user[rid]
                # Удаляем из completed_responses тоже
                self.completed_responses.discard(rid)

            logger.info(f"🗑️ Очищен стрим для пользователя {user_id}")

    async def update_message(self, user_id, text):
        """Обновление сообщения (переопределяется в основном коде)."""
        pass

    async def finalize_message(self, user_id, text):
        """Финализация сообщения (переопределяется в основном коде)."""
        pass

    async def send_quota_error_message(self, user_id):
        """Отправка сообщения об ошибке квоты (переопределяется в основном коде)."""
        pass

    async def cleanup_stale_streams(self):
        """Очистка очень старых стримов (старше 24 часов)."""
        current_time = asyncio.get_event_loop().time()
        very_old_users = []

        for user_id, stream_data in self.active_streams.items():
            # Очищаем только очень старые стримы (старше 24 часов = 86400 секунд)
            created_at = stream_data.get("created_at", current_time)
            age = current_time - created_at

            if age > 86400:  # 24 часа
                very_old_users.append(user_id)
                logger.warning(
                    f"🧹 Обнаружен очень старый стрим для пользователя {user_id} (возраст: {age / 3600:.1f} часов)")

        # Очищаем только очень старые стримы
        for user_id in very_old_users:
            try:
                logger.info(f"🗑️ Очищаем старый стрим для пользователя {user_id}")

                # Удаляем из словарей
                stream_data = self.active_streams.get(user_id, {})
                response_id = stream_data.get("response_id")

                self.active_streams.pop(user_id, None)
                if response_id:
                    self.response_to_user.pop(response_id, None)
                    self.completed_responses.discard(response_id)

                logger.info(f"Очищен старый стрим для пользователя {user_id}")
            except Exception as e:
                logger.error(f" Ошибка при очистке старого стрима для пользователя {user_id}: {e}")

        return len(very_old_users)

    def get_stream_stats(self):
        """Получить статистику стримов для диагностики."""
        current_time = asyncio.get_event_loop().time()
        stats = {
            "active_streams": len(self.active_streams),
            "response_mappings": len(self.response_to_user),
            "completed_responses": len(self.completed_responses),
            "is_connected": self.is_connected,
            "stream_ages": {},
            "completed_stream_count": 0,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": round(self.total_cost, 4)
        }

        for user_id, stream_data in self.active_streams.items():
            last_update = stream_data.get("last_update", 0)
            age = current_time - last_update if last_update > 0 else 0
            stats["stream_ages"][user_id] = age

            # Проверяем, завершен ли response
            response_id = stream_data.get("response_id")
            if response_id and response_id in self.completed_responses:
                stats["completed_stream_count"] += 1

        return stats


# Глобальные переменные
realtime_client = None
yclients_adapter = None
bot_instance = None
user_inactivity_timers: Dict[int, asyncio.Task] = {}  # user_id -> timer task

# Таймаут неактивности (1 час)
INACTIVITY_TIMEOUT = 3600  # секунд

# Глобальные счетчики для стоимости
total_input_tokens = 0
total_output_tokens = 0
total_cost = 0.0


# Функции для работы с таймаутами неактивности
async def reset_user_inactivity_timer(user_id: int):
    """Сбрасывает таймер неактивности для пользователя."""
    global user_inactivity_timers
    
    # Отменяем существующий таймер
    if user_id in user_inactivity_timers:
        user_inactivity_timers[user_id].cancel()
    
    # Создаем новый таймер
    async def timeout_handler():
        try:
            await asyncio.sleep(INACTIVITY_TIMEOUT)
            logger.info(f"⏰ Таймаут неактивности для пользователя {user_id}")
            
            # Отменяем активный стрим пользователя
            if realtime_client:
                await realtime_client.cancel_stream(user_id)
            
            # Удаляем таймер
            if user_id in user_inactivity_timers:
                del user_inactivity_timers[user_id]
                
        except asyncio.CancelledError:
            # Таймер был отменен - это нормально
            pass
        except Exception as e:
            logger.error(f"Ошибка в обработчике таймаута неактивности: {e}")
    
    # Запускаем новый таймер
    user_inactivity_timers[user_id] = asyncio.create_task(timeout_handler())
    logger.debug(f"🔄 Таймер неактивности сброшен для пользователя {user_id}")


async def cancel_user_inactivity_timer(user_id: int):
    """Отменяет таймер неактивности для пользователя."""
    global user_inactivity_timers
    
    if user_id in user_inactivity_timers:
        user_inactivity_timers[user_id].cancel()
        del user_inactivity_timers[user_id]
        logger.debug(f"❌ Таймер неактивности отменен для пользователя {user_id}")


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """
    Расчет стоимости токенов для GPT-4o Realtime API.
    Цены на декабрь 2024:
    - Input tokens: $2.50 / 1M tokens
    - Output tokens: $10.00 / 1M tokens
    """
    input_cost = (input_tokens / 1_000_000) * 2.50
    output_cost = (output_tokens / 1_000_000) * 10.00
    return input_cost + output_cost


def update_token_usage(usage_data: dict):
    """Обновляет счетчики токенов и стоимости."""
    global total_input_tokens, total_output_tokens, total_cost
    
    if not usage_data:
        return

    input_tokens = usage_data.get('input_tokens', 0)
    output_tokens = usage_data.get('output_tokens', 0)

    total_input_tokens += input_tokens
    total_output_tokens += output_tokens

    session_cost = calculate_cost(input_tokens, output_tokens)
    total_cost += session_cost

    logger.info(
        f"💰 Токены: {input_tokens} вход + {output_tokens} выход = ${session_cost:.4f} (всего: ${total_cost:.4f})")


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    """Обработчик /start."""
    user_id = message.from_user.id
    user_name = message.from_user.first_name if message.from_user else "Пациент"
    
    # Проверяем, есть ли уже профиль пользователя
    try:
        profile_result = await yclients_adapter.get_user_profile(user_id)
        has_profile = profile_result is not None
    except Exception as e:
        logger.warning(f"Ошибка проверки профиля пользователя {user_id}: {e}")
        has_profile = False

    # Если профиля нет, пытаемся получить информацию из Telegram
    if not has_profile:
        try:
            telegram_profile = await yclients_adapter.get_telegram_profile(user_id)
            if telegram_profile.get("success"):
                data = telegram_profile["data"]
                telegram_name = data.get("telegram_first_name") or user_name
                logger.info(f"📱 Получен Telegram профиль для {user_id}: {telegram_name}")
                
                # Создаем базовый профиль с информацией из Telegram
                try:
                    # Создаем профиль с Telegram данными
                    await yclients_adapter.get_or_create_user_profile(
                        telegram_id=user_id,
                        name=telegram_name
                    )
                    logger.info(f"✅ Создан профиль из Telegram данных для {user_id}")
                except Exception as profile_error:
                    logger.error(f"Ошибка создания профиля из Telegram: {profile_error}")
            else:
                logger.info(f"❌ Telegram профиль недоступен для {user_id}: {telegram_profile.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Ошибка получения Telegram профиля: {e}")

    await message.answer(
        f"🦷 <b>Добро пожаловать в стоматологию «Белые зубы»!</b>\n\n"
        f"Здравствуйте, {user_name}! Я ваш AI-консультант.\n\n"
        f"<b>Я помогу вам:</b>\n"
        f"• 📋 Записаться на прием к врачу\n"
        f"• 💰 Узнать цены на услуги\n"
        f"• 👨‍⚕️ Выбрать подходящего специалиста\n"
        f"• 📅 Найти удобное время\n"
        f"• 🏥 Получить информацию о клинике\n\n"
        f"<i>Просто напишите, что вас интересует!</i>\n\n"
        f"<b>Примеры вопросов:</b>\n"
        f"• \"Сколько стоит лечение кариеса?\"\n"
        f"• \"Хочу записаться к стоматологу\"\n"
        f"• \"Покажите ваших врачей\"\n"
        f"• \"Где находится клиника?\"",
        parse_mode="HTML"
    )


@router.message(F.text)
async def text_handler(message: Message) -> None:
    """Обработчик текстовых сообщений."""
    if not realtime_client or not realtime_client.is_connected:
        await message.answer(
            " <b>Временные технические проблемы</b>\n\n"
            "AI-консультант временно недоступен.\n"
            "Пожалуйста, обратитесь по телефону:\n"
            "📞 +7 (495) 123-45-67",
            parse_mode="HTML"
        )
        return

    # Отправляем "думаю..."
    thinking_msg = await message.answer("<i>...</i>", parse_mode="HTML")
    last_sent_text = ""  # Отслеживаем последний отправленный текст для избежания дублирования
    finalization_lock = asyncio.Lock()  # Блокировка для предотвращения одновременных финализаций

    try:
        # Настраиваем коллбеки для обновления сообщения
        async def update_message_callback(user_id, text):
            nonlocal last_sent_text
            if text.strip() and text != last_sent_text:
                try:
                    # Отображаем текст как есть, убираем возможные артефакты курсора
                    streaming_text = text.replace(" <i>_</i>", "").replace(" <i> </i>", "")
                    # Убираем одиночные подчеркивания в конце строки (артефакты курсора)
                    streaming_text = re.sub(r'\s*_\s*$', '', streaming_text)
                    await thinking_msg.edit_text(streaming_text, parse_mode="HTML")
                    last_sent_text = text  # Сохраняем отправленный текст (без курсора)
                    logger.debug(f"📝 Обновлено сообщение для пользователя {user_id} (длина: {len(text)})")
                except Exception as e:
                    error_msg = str(e)
                    if "Flood control exceeded" in error_msg or "Too Many Requests" in error_msg:
                        logger.debug(f"⏳ Rate limit для пользователя {user_id}, пропускаем обновление")
                    elif "message is not modified" in error_msg:
                        logger.debug(f"📝 Сообщение не изменилось для пользователя {user_id}")
                    else:
                        logger.warning(f"⚠️ Ошибка при обновлении сообщения для пользователя {user_id}: {e}")

        async def finalize_message_callback(user_id, text):
            nonlocal last_sent_text

            # Используем блокировку для предотвращения одновременных финализаций
            async with finalization_lock:
                try:
                    logger.info(f"Финализация сообщения для пользователя {user_id}")

                    # Проверяем состояние стрима через connection pool
                    stream_state = connection_pool.get_user_stream_state(user_id)
                    if stream_state and stream_state.finalized:
                        logger.info(f"Сообщение уже финализировано для пользователя {user_id}, пропускаем")
                        return

                    # Используем текст как есть, убираем возможные артефакты курсора
                    final_text = text.replace(" <i>_</i>", "").replace(" <i> </i>", "").replace("_", "").strip()

                    # Проверяем, отличается ли финальный текст от последнего отправленного
                    # или если финальный текст длиннее (могли пропустить дельты)
                    if final_text != last_sent_text or len(final_text) > len(last_sent_text):
                        await thinking_msg.edit_text(final_text, parse_mode="HTML")
                        last_sent_text = final_text
                        logger.info(
                            f"Финальное сообщение отправлено пользователю {user_id} (длина: {len(final_text)})")
                    else:
                        logger.info(
                            f"Финальный текст идентичен последнему отправленному, пропускаем обновление для пользователя {user_id}")

                    # Помечаем как завершенный для избежания повторных вызовов
                    if message.from_user.id in dental_client.active_streams:
                        stream_data = dental_client.active_streams[message.from_user.id]
                        stream_data["completed"] = True
                        stream_data["finalized"] = True  # Флаг что сообщение уже отправлено
                        logger.info(
                            f"Сообщение отправлено пользователю {message.from_user.id}, ждем response.done для очистки")

                except Exception as e:
                    error_msg = str(e)
                    if "Flood control exceeded" in error_msg or "Too Many Requests" in error_msg:
                        logger.warning(f"⏳ Rate limit в финализации для пользователя {user_id}, попробуем позже")
                        # Попытка отправить через несколько секунд
                        await asyncio.sleep(5)
                        try:
                            await thinking_msg.edit_text(final_text, parse_mode="HTML")
                            logger.info(f"Финальное сообщение отправлено после задержки для пользователя {user_id}")
                        except Exception as retry_e:
                            logger.error(f" Повторная ошибка финализации для пользователя {user_id}: {retry_e}")
                    else:
                        logger.error(f" Ошибка финализации сообщения для пользователя {user_id}: {e}")

        # Коллбек для ошибки квоты
        async def quota_error_callback(user_id):
            try:
                await thinking_msg.edit_text(
                    "💳 <b>Временные технические проблемы</b>\n\n"
                    "AI-консультант временно недоступен из-за превышения лимитов API.\n\n"
                    "🔧 <b>Что делать:</b>\n"
                    "• Попробуйте позже через 10-15 минут\n"
                    "• Или обратитесь напрямую по телефону:\n\n"
                    "📞 <b>+7 (495) 123-45-67</b>\n\n"
                    "Извините за неудобства! 😔",
                    parse_mode="HTML"
                )
                logger.info(f"📤 Отправлено сообщение об ошибке квоты пользователю {user_id}")
            except Exception as e:
                logger.error(f" Ошибка при отправке сообщения об ошибке квоты: {e}")

        # Сбрасываем таймер неактивности
        await reset_user_inactivity_timer(message.from_user.id)

        # Отправляем сообщение через connection pool
        stream_controller, connection_id = await connection_pool.send_user_message(
            message.from_user.id,
            message.text,
            thinking_msg.message_id
        )
        
        # Устанавливаем коллбеки для stream controller
        stream_controller.on_text_delta = update_message_callback
        stream_controller.on_text_done = finalize_message_callback
        stream_controller.on_error = quota_error_callback
        
        logger.info(f"📤 Сообщение отправлено через connection #{connection_id}")

        # Добавляем таймаут - если через 60 секунд нет ответа, показываем ошибку
        async def timeout_handler():
            user_id = message.from_user.id
            await asyncio.sleep(60)

            # Проверяем состояние стрима через connection pool
            stream_state = connection_pool.get_user_stream_state(user_id)
            if stream_state:
                # Если стрим уже завершен, не обрабатываем таймаут
                if stream_state.completed:
                    logger.info(f"ℹ️ Стрим для пользователя {user_id} уже завершен, таймаут не нужен")
                    return

                logger.warning(f"⏰ Таймаут для пользователя {user_id}")
                logger.info(f"📝 Накопленный текст: '{stream_state.accumulated_text[:100]}...'")

                # Получаем статистику для диагностики
                stats = connection_pool.get_pool_stats()
                logger.info(f"📊 Статистика connection pool при таймауте: {stats}")

                # Проверяем, есть ли уже текст для отправки
                if stream_state.accumulated_text.strip():
                    logger.info(f"💡 Есть накопленный текст, отправляем его вместо ошибки")
                    try:
                        # Отправляем накопленный текст как финальный ответ, убираем артефакты курсора
                        final_accumulated_text = stream_state.accumulated_text.replace(" <i>_</i>", "").replace(" <i> </i>", "").replace("_", "").strip()
                        await thinking_msg.edit_text(final_accumulated_text, parse_mode="HTML")

                        # Отменяем стрим
                        await connection_pool.cancel_user_stream(user_id)
                        logger.info(f"Отправлен накопленный текст для пользователя {user_id}")
                        return

                    except Exception as e:
                        logger.error(f" Ошибка при отправке накопленного текста: {e}")

                try:
                    # Отменяем стрим корректно
                    await connection_pool.cancel_user_stream(user_id)

                    # Показываем сообщение об ошибке
                    await thinking_msg.edit_text(
                        "⏰ <b>Извините, обработка запроса заняла слишком много времени</b>\n\n"
                        "Попробуйте задать вопрос проще или обратитесь по телефону:\n"
                        "📞 +7 (495) 123-45-67",
                        parse_mode="HTML"
                    )

                except Exception as timeout_error:
                    logger.error(f" Ошибка при обработке таймаута для пользователя {user_id}: {timeout_error}")

        # Создаем задачу таймаута
        timeout_task = asyncio.create_task(timeout_handler())

        # Сохраняем ссылку на задачу для возможной отмены
        if hasattr(dental_client.active_streams.get(message.from_user.id, {}), '__dict__'):
            dental_client.active_streams[message.from_user.id]["timeout_task"] = timeout_task

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await thinking_msg.edit_text(
            "😔 <b>Произошла ошибка</b>\n\n"
            "Не удалось обработать ваш запрос.\n"
            "Попробуйте еще раз или обратитесь по телефону:\n"
            "📞 +7 (495) 123-45-67",
            parse_mode="HTML"
        )


def acquire_lock():
    """Получить блокировку для предотвращения множественного запуска."""
    lock_file = "/tmp/dental_bot.lock"
    try:
        lock_fd = open(lock_file, 'w')
        fcntl.lockf(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return lock_fd
    except IOError:
        print(" Ошибка: Другой экземпляр бота уже запущен!")
        print("🔍 Проверьте процессы: ps aux | grep dental_bot")
        sys.exit(1)


async def main():
    """Главная функция."""
    global bot_instance, connection_pool, yclients_adapter

    # Проверка блокировки
    lock_fd = acquire_lock()
    print("🔒 Блокировка получена, запуск единственного экземпляра бота")

    token = os.getenv("TG_BOT_TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        logger.error(" Токен бота не найден!")
        return

    if not os.getenv("OPENAI_API_KEY"):
        logger.error(" OpenAI API ключ не найден!")
        return

    # Инициализируем YClients адаптер
    yclients_adapter = get_yclients_adapter()
    logger.info("✅ YClients адаптер инициализирован")

    # Создаем connection pool
    try:
        connection_pool = await get_connection_pool(yclients_adapter)
        logger.info("🏊 Connection pool создан и инициализирован")
    except Exception as e:
        logger.error(f" Не удалось создать connection pool: {e}")
        return

    # Создаем бота
    bot_instance = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)

    # Создаем и запускаем админ-сервер
    admin_port = int(os.getenv("ADMIN_PORT", "8080"))
    admin_server = AdminServer(yclients_adapter, port=admin_port)
    admin_runner = await admin_server.start()

    # Запускаем фоновую задачу очистки зависших стримов и кеша
    async def cleanup_background_task():
        """Фоновая задача для очистки зависших стримов и истекших записей кеша."""
        while True:
            try:
                await asyncio.sleep(21600)  # Проверяем каждые 6 часов

                # Выполняем health check connection pool
                await connection_pool.health_check()

                # Очищаем истекшие записи всех кешей
                expired_doctors_cache = doctors_cache.cleanup_expired()
                expired_services_cache = services_cache.cleanup_expired()

                total_expired = expired_doctors_cache + expired_services_cache
                if total_expired > 0:
                    logger.info(
                        f"🗑️ Очищено истекших записей: врачи={expired_doctors_cache}, услуги={expired_services_cache}")

                # Логируем статистику
                stats = connection_pool.get_pool_stats()
                doctors_cache_stats = doctors_cache.get_stats()
                services_cache_stats = services_cache.get_stats()

                logger.info(f"📊 Статистика connection pool: {stats}")
                logger.info(f"💾 Статистика кеша врачей: {doctors_cache_stats}")
                logger.info(f"💾 Статистика кеша услуг: {services_cache_stats}")

            except Exception as e:
                logger.error(f" Ошибка в фоновой задаче очистки: {e}")
                await asyncio.sleep(60)  # При ошибке ждем дольше

    cleanup_task = asyncio.create_task(cleanup_background_task())
    logger.info("🧹 Запущена фоновая задача очистки зависших стримов")

    logger.info("🦷 Запускаем бота-консультанта стоматологической клиники...")

    try:
        await dp.start_polling(bot_instance, skip_updates=True)
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")
    finally:
        cleanup_task.cancel()
        logger.info("🛑 Остановка фоновых задач")

        # Останавливаем админ-сервер
        if 'admin_runner' in locals():
            await admin_runner.cleanup()
            logger.info("🌐 Админ-сервер остановлен")

        # Отменяем все таймеры неактивности
        for user_id in list(user_inactivity_timers.keys()):
            await cancel_user_inactivity_timer(user_id)

        # Финальная статистика
        if connection_pool:
            final_stats = connection_pool.get_pool_stats()
            logger.info(f"📊 Финальная статистика connection pool: {final_stats}")
        
        if yclients_adapter:
            final_cache_stats = yclients_adapter.get_all_cache_stats()
            logger.info(f"💾 Финальная статистика кешей: {final_cache_stats}")
            
        logger.info(f"💰 Общие расходы за сессию: ${total_cost:.4f}")

        await bot_instance.session.close()
        
        # Очищаем connection pool
        if connection_pool:
            await cleanup_connection_pool()


if __name__ == "__main__":
    asyncio.run(main())
