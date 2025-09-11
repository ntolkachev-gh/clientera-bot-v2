#!/usr/bin/env python3
"""
Telegram-бот консультант для стоматологической клиники с OpenAI Realtime API.
Использует src/realtime/client.py в качестве основы.
"""

import asyncio
import fcntl
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta
from typing import Dict

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
import aiohttp
from aiohttp import web

# Импорт realtime клиента и интеграций
from src.integrations.yclients_adapter import get_yclients_adapter
from src.realtime.client import get_realtime_client, cleanup_realtime_client

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

# Глобальные переменные
realtime_client = None
yclients_adapter = None
bot_instance = None
user_inactivity_timers: Dict[int, asyncio.Task] = {}

# Таймаут неактивности (1 час)
INACTIVITY_TIMEOUT = 3600

# Время запуска
start_time = time.time()


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
            try:
                user_realtime_client = await get_realtime_client(yclients_adapter, user_id)
                await user_realtime_client.cancel_stream(user_id)
            except Exception as e:
                logger.error(f"Ошибка отмены стрима для пользователя {user_id}: {e}")
            
            # Удаляем таймер
            if user_id in user_inactivity_timers:
                del user_inactivity_timers[user_id]
                
        except asyncio.CancelledError:
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
                    await yclients_adapter.get_or_create_user_profile(
                        telegram_id=user_id,
                        name=telegram_name
                    )
                    logger.info(f"✅ Создан профиль из Telegram данных для {user_id}")
                except Exception as profile_error:
                    logger.error(f"Ошибка создания профиля из Telegram: {profile_error}")
            else:
                logger.info(f"❌ Telegram профиль недоступен для {user_id}")
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
    user_id = message.from_user.id
    
    # Получаем персональный realtime client для этого пользователя
    try:
        realtime_client = await get_realtime_client(yclients_adapter, user_id)
        if not realtime_client.is_connected:
            await message.answer(
                " <b>Временные технические проблемы</b>\n\n"
                "AI-консультант временно недоступен.\n"
                "Пожалуйста, обратитесь по телефону:\n"
                "📞 +7 (495) 123-45-67",
                parse_mode="HTML"
            )
            return
    except Exception as e:
        logger.error(f"Ошибка получения realtime client для пользователя {user_id}: {e}")
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
    last_sent_text = ""
    last_update_time = 0
    finalization_lock = asyncio.Lock()

    try:
        # Настраиваем коллбеки для обновления сообщения с throttling
        async def update_message_callback(user_id, text):
            nonlocal last_sent_text, last_update_time
            
            current_time = time.time()
            
            # Throttling: обновляем максимум раз в 500мс или если текст значительно изменился
            should_update = (
                current_time - last_update_time > 0.5 or  # Минимум 500мс между обновлениями
                len(text) - len(last_sent_text) > 50 or   # Или если добавилось много текста
                text.endswith(('.', '!', '?', '\n')) and not last_sent_text.endswith(('.', '!', '?', '\n'))  # Или завершилось предложение
            )
            
            if text.strip() and text != last_sent_text and should_update:
                try:
                    # Убираем возможные артефакты курсора
                    streaming_text = text.replace(" <i>_</i>", "").replace(" <i> </i>", "")
                    streaming_text = re.sub(r'\s*_\s*$', '', streaming_text)
                    await thinking_msg.edit_text(streaming_text, parse_mode="HTML")
                    last_sent_text = text
                    last_update_time = current_time
                    logger.debug(f"📝 Обновлено сообщение для пользователя {user_id} (длина: {len(text)})")
                except Exception as e:
                    error_msg = str(e)
                    if "Flood control exceeded" in error_msg or "Too Many Requests" in error_msg:
                        logger.debug(f"⏳ Rate limit для пользователя {user_id}, пропускаем обновление")
                        # При rate limit увеличиваем интервал
                        last_update_time = current_time + 1.0  # Дополнительная задержка
                    elif "message is not modified" in error_msg:
                        logger.debug(f"📝 Сообщение не изменилось для пользователя {user_id}")
                    else:
                        logger.warning(f"⚠️ Ошибка при обновлении сообщения для пользователя {user_id}: {e}")
            elif text.strip() and text != last_sent_text:
                # Сохраняем текст даже если не обновляли, чтобы финализация работала правильно
                last_sent_text = text

        async def finalize_message_callback(user_id, text):
            nonlocal last_sent_text

            async with finalization_lock:
                try:
                    logger.info(f"Финализация сообщения для пользователя {user_id}")

                    # Проверяем состояние стрима
                    stream_state = realtime_client.get_stream_state(user_id)
                    if stream_state and stream_state == "done":
                        logger.info(f"Сообщение уже финализировано для пользователя {user_id}, пропускаем")
                        return

                    # Убираем артефакты курсора
                    final_text = text.replace(" <i>_</i>", "").replace(" <i> </i>", "").replace("_", "").strip()

                    # ВСЕГДА обновляем в финализации для гарантии полного текста
                    if final_text.strip():
                        await thinking_msg.edit_text(final_text, parse_mode="HTML")
                        logger.info(f"✅ Финальное сообщение отправлено пользователю {user_id} (длина: {len(final_text)})")
                        
                        # Проверяем, был ли текст обрезан из-за throttling
                        if len(final_text) > len(last_sent_text) + 10:
                            logger.info(f"📈 Финальный текст длиннее последнего обновления на {len(final_text) - len(last_sent_text)} символов")
                        
                        last_sent_text = final_text
                    else:
                        logger.warning(f"⚠️ Финальный текст пустой для пользователя {user_id}")

                except Exception as e:
                    error_msg = str(e)
                    if "Flood control exceeded" in error_msg or "Too Many Requests" in error_msg:
                        logger.warning(f"⏳ Rate limit в финализации для пользователя {user_id}")
                        await asyncio.sleep(5)
                        try:
                            await thinking_msg.edit_text(final_text, parse_mode="HTML")
                            logger.info(f"Финальное сообщение отправлено после задержки для пользователя {user_id}")
                        except Exception as retry_e:
                            logger.error(f"Повторная ошибка финализации для пользователя {user_id}: {retry_e}")
                    else:
                        logger.error(f"Ошибка финализации сообщения для пользователя {user_id}: {e}")

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
                logger.error(f"Ошибка при отправке сообщения об ошибке квоты: {e}")

        # Сбрасываем таймер неактивности
        await reset_user_inactivity_timer(user_id)
        
        # ВАЖНО: Устанавливаем коллбеки ДО отправки сообщения
        # Создаем предварительный stream и устанавливаем коллбеки
        from src.realtime.events import StreamController, StreamState
        
        # Создаем stream заранее и устанавливаем коллбеки
        temp_stream = StreamController(
            user_id=user_id,
            message_id=thinking_msg.message_id,
            state=StreamState.IDLE
        )
        realtime_client.active_streams[user_id] = temp_stream
        
        # Устанавливаем коллбеки до отправки с дополнительным логированием
        async def delta_wrapper(delta, accumulated):
            logger.debug(f"🔄 Delta для {user_id}: +{len(delta)} символов, всего: {len(accumulated)}")
            await update_message_callback(user_id, accumulated)
            
        async def done_wrapper(final_text):
            logger.info(f"✅ Финализация для {user_id}: {len(final_text)} символов")
            await finalize_message_callback(user_id, final_text)
            
        async def error_wrapper(error):
            logger.error(f"❌ Ошибка стрима для {user_id}: {error}")
            await quota_error_callback(user_id)
        
        realtime_client.set_stream_callbacks(
            user_id,
            on_delta=lambda delta, accumulated: asyncio.create_task(delta_wrapper(delta, accumulated)),
            on_done=lambda final_text: asyncio.create_task(done_wrapper(final_text)),
            on_error=lambda error: asyncio.create_task(error_wrapper(error))
        )
        
        # Теперь отправляем сообщение - коллбеки уже готовы
        try:
            # Create conversation item
            create_event = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": message.text}]
                }
            }
            await realtime_client._send_event(create_event)
            
            # Create response
            response_event = {"type": "response.create"}
            await realtime_client._send_event(response_event)
            
            logger.info(f"📤 Сообщение отправлено с предустановленными коллбеками")
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            # Очищаем stream при ошибке
            realtime_client.active_streams.pop(user_id, None)
            raise
        
        logger.info(f"📤 Сообщение отправлено через realtime client")

        # Добавляем таймаут - если через 60 секунд нет ответа, показываем ошибку
        async def timeout_handler():
            user_id = message.from_user.id
            
            # Сначала ждем 15 секунд - если за это время нет текстового ответа после function call
            await asyncio.sleep(15)
            
            stream_controller = realtime_client.active_streams.get(user_id)
            if stream_controller and not stream_controller.accumulated_text.strip():
                # Если через 15 секунд нет текста, возможно function call завис
                logger.warning(f"⚠️ Через 15 секунд нет текстового ответа для {user_id}, проверяем...")
                logger.info(f"🔍 Состояние стрима: {stream_controller.state}")
                
                # Проверяем, не было ли уже попыток восстановления
                retry_count = getattr(stream_controller, 'retry_count', 0)
                if retry_count >= 2:
                    logger.warning(f"⚠️ Превышено количество попыток восстановления для {user_id}, завершаем")
                    await realtime_client.cancel_stream(user_id)
                    return
                
                # Увеличиваем счетчик попыток
                stream_controller.retry_count = retry_count + 1
                
                # Сначала отменяем текущий ответ, если он есть
                try:
                    await realtime_client.cancel_stream(user_id)
                    logger.info(f"❌ Отменили зависший ответ для {user_id}")
                    await asyncio.sleep(2)  # Даем больше времени на отмену
                except Exception as e:
                    logger.error(f"Ошибка отмены ответа: {e}")
                
                # НЕ создаем новый response здесь - пусть система сама восстановится
                logger.info(f"🔄 Ждем автоматического восстановления для {user_id} (попытка {retry_count + 1}/2)")
            
            # Затем ждем еще 45 секунд (общий таймаут 60 секунд)
            await asyncio.sleep(45)

            # Проверяем состояние стрима
            stream_state = realtime_client.get_stream_state(user_id)
            if stream_state:
                # Если стрим уже завершен, не обрабатываем таймаут
                if stream_state in ["done", "error", "cancelled"]:
                    logger.info(f"ℹ️ Стрим для пользователя {user_id} уже завершен ({stream_state}), таймаут не нужен")
                    return

                logger.warning(f"⏰ Таймаут для пользователя {user_id}")

                # Получаем stream controller для доступа к accumulated_text
                stream_controller = realtime_client.active_streams.get(user_id)
                if stream_controller and stream_controller.accumulated_text.strip():
                    logger.info(f"💡 Есть накопленный текст, отправляем его вместо ошибки")
                    try:
                        final_accumulated_text = stream_controller.accumulated_text.replace(" <i>_</i>", "").replace(" <i> </i>", "").replace("_", "").strip()
                        await thinking_msg.edit_text(final_accumulated_text, parse_mode="HTML")
                        await realtime_client.cancel_stream(user_id)
                        logger.info(f"Отправлен накопленный текст для пользователя {user_id}")
                        return
                    except Exception as e:
                        logger.error(f"Ошибка при отправке накопленного текста: {e}")

                try:
                    await realtime_client.cancel_stream(user_id)
                    await thinking_msg.edit_text(
                        "⏰ <b>Извините, AI-консультант не отвечает</b>\n\n"
                        "Возможные причины:\n"
                        "• Высокая нагрузка на сервис\n"
                        "• Технические проблемы с AI\n"
                        "• Сложный запрос требует больше времени\n\n"
                        "<b>Что делать:</b>\n"
                        "• Попробуйте задать вопрос проще\n"
                        "• Или обратитесь напрямую:\n"
                        "📞 +7 (495) 123-45-67",
                        parse_mode="HTML"
                    )
                except Exception as timeout_error:
                    logger.error(f"Ошибка при обработке таймаута для пользователя {user_id}: {timeout_error}")

        # Создаем задачу таймаута
        timeout_task = asyncio.create_task(timeout_handler())
        
        # Добавляем периодическую проверку для предотвращения "заедания"
        async def periodic_check():
            """Периодически проверяем и принудительно обновляем сообщение."""
            nonlocal last_sent_text, last_update_time
            
            for i in range(12):  # Проверяем 12 раз с интервалом 5 секунд = 60 секунд
                await asyncio.sleep(5)
                
                stream_controller = realtime_client.active_streams.get(user_id)
                if not stream_controller:
                    break
                
                # Проверяем, не застрял ли function call без текстового ответа
                if (i >= 4 and  # Прошло 20+ секунд
                    not stream_controller.accumulated_text.strip() and 
                    stream_controller.state == "idle"):
                    
                    logger.warning(f"🔧 Function call выполнился, но нет текстового ответа для {user_id}")
                    logger.info(f"🔍 Детали стрима: state={stream_controller.state}, text_length={len(stream_controller.accumulated_text)}")
                    
                    try:
                        # Отменяем текущий ответ и запрашиваем новый
                        cancel_event = {"type": "response.cancel"}
                        await realtime_client._send_event(cancel_event)
                        await asyncio.sleep(0.5)
                        
                        response_event = {"type": "response.create"}
                        await realtime_client._send_event(response_event)
                        logger.info(f"🔄 Принудительный запрос генерации для {user_id}")
                    except Exception as e:
                        logger.error(f"Ошибка принудительного запроса: {e}")
                    
                # Если есть накопленный текст, но сообщение давно не обновлялось
                elif (stream_controller.accumulated_text.strip() and 
                      stream_controller.accumulated_text != last_sent_text and
                      time.time() - last_update_time > 3):  # Более 3 секунд без обновления
                    
                    logger.info(f"🔧 Принудительное обновление сообщения для {user_id} (застряло)")
                    try:
                        clean_text = stream_controller.accumulated_text.replace(" <i>_</i>", "").replace(" <i> </i>", "").strip()
                        await thinking_msg.edit_text(clean_text, parse_mode="HTML")
                        last_sent_text = stream_controller.accumulated_text
                        last_update_time = time.time()
                    except Exception as e:
                        logger.error(f"Ошибка принудительного обновления: {e}")
                
                # Если стрим завершен, выходим
                if stream_controller.state in ["done", "error", "cancelled"]:
                    break
        
        # Запускаем периодическую проверку
        periodic_task = asyncio.create_task(periodic_check())

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
        print("❌ Ошибка: Другой экземпляр бота уже запущен!")
        print("🔍 Проверьте процессы: ps aux | grep dental_bot")
        sys.exit(1)


async def main():
    """Главная функция."""
    global bot_instance, realtime_client, yclients_adapter

    # Проверка блокировки
    lock_fd = acquire_lock()
    print("🔒 Блокировка получена, запуск единственного экземпляра бота")

    token = os.getenv("TG_BOT_TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        logger.error("❌ Токен бота не найден!")
        return

    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OpenAI API ключ не найден!")
        return

    # Инициализируем YClients адаптер
    yclients_adapter = get_yclients_adapter()
    logger.info("✅ YClients адаптер инициализирован")

    # Инициализируем realtime client manager (создается при первом использовании)
    logger.info("🤖 Realtime client manager готов к работе")

    # Создаем бота
    bot_instance = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)

    # Запускаем фоновую задачу для health check
    async def health_check_task():
        """Фоновая задача для проверки здоровья realtime clients."""
        while True:
            try:
                await asyncio.sleep(3600)  # Проверяем каждый час
                
                # Здесь можно добавить проверку состояния менеджера клиентов
                # но в основном он сам управляет соединениями
                logger.info("🏥 Health check завершен")
                
            except Exception as e:
                logger.error(f"❌ Ошибка в health check: {e}")
                await asyncio.sleep(60)

    health_task = asyncio.create_task(health_check_task())
    logger.info("🏥 Запущена задача health check")

    # Создаем HTTP сервер для health check (для Railway)
    app = web.Application()
    
    async def health_check_handler(request):
        """Health check endpoint для Railway."""
        try:
            # Проверяем, что бот работает
            me = await bot_instance.get_me()
            return web.json_response({
                "status": "healthy",
                "bot_info": {
                    "id": me.id,
                    "username": me.username,
                    "first_name": me.first_name
                },
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return web.json_response({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }, status=503)
    
    app.router.add_get('/health', health_check_handler)
    
    # Запускаем HTTP сервер в фоне
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logger.info("🌐 HTTP сервер запущен на порту 8080 для health check")

    logger.info("🦷 Запускаем бота-консультанта стоматологической клиники...")

    try:
        await dp.start_polling(bot_instance, skip_updates=True)
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")
    finally:
        health_task.cancel()
        logger.info("🛑 Остановка фоновых задач")
        
        # Останавливаем HTTP сервер
        try:
            await site.stop()
            await runner.cleanup()
            logger.info("🛑 HTTP сервер остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке HTTP сервера: {e}")

        # Отменяем все таймеры неактивности
        for user_id in list(user_inactivity_timers.keys()):
            await cancel_user_inactivity_timer(user_id)

        # Финальная статистика
        try:
            from src.realtime.client import _client_manager
            if _client_manager:
                stats = _client_manager.get_stats()
                logger.info(f"📊 Финальная статистика realtime clients: {stats}")
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
        
        if yclients_adapter:
            cache_stats = yclients_adapter.get_all_cache_stats()
            logger.info(f"💾 Финальная статистика кешей: {cache_stats}")

        await bot_instance.session.close()
        
        # Очищаем realtime client
        if realtime_client:
            await cleanup_realtime_client()


if __name__ == "__main__":
    asyncio.run(main())
