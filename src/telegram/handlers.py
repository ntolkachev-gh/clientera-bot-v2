#!/usr/bin/env python3
"""
Telegram bot handlers with Realtime API streaming support.
"""

import asyncio
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from ..integrations.yclients_adapter import get_yclients_adapter
from ..realtime.client import get_realtime_client
from ..realtime.connection_pool import get_connection_pool
from ..realtime.events import StreamState
from ..utils.logger import get_logger
from ..utils.throttler import get_message_throttler, get_rate_limiter

logger = get_logger(__name__)
router = Router()

# Global instances
throttler = get_message_throttler()
rate_limiter = get_rate_limiter()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    """Handle /start command."""
    user_id = message.from_user.id if message.from_user else 0
    user_name = message.from_user.first_name if message.from_user else "Пользователь"
    
    logger.info(f"Start command from user {user_id}")
    
    welcome_text = f"""🦷 <b>Добро пожаловать в стоматологию «Белые зубы»!</b>

Привет, {user_name}! Я — ваш AI-ассистент. Помогу:

📋 <b>Записаться на прием</b>
💰 <b>Узнать цены на услуги</b>
👨‍⚕️ <b>Выбрать врача</b>
📅 <b>Найти свободное время</b>
🏥 <b>Получить информацию о филиалах</b>

<i>Просто напишите, что вас интересует, и я помогу!</i>

Например:
• "Хочу записаться к терапевту"
• "Сколько стоит лечение кариеса?"
• "Покажи свободные слоты на завтра"
"""
    
    await message.answer(welcome_text, parse_mode="HTML")


@router.message(Command("stats"))
async def stats_handler(message: Message) -> None:
    """Handle /stats command - show connection pool statistics."""
    user_id = message.from_user.id if message.from_user else 0
    
    logger.info(f"Stats command from user {user_id}")
    
    try:
        yclients_adapter = get_yclients_adapter()
        connection_pool = await get_connection_pool(yclients_adapter)
        
        stats = connection_pool.get_pool_stats()
        
        stats_text = f"""📊 <b>Статистика пула соединений</b>

🔌 <b>Соединения:</b>
• Активных: {stats['healthy_connections']}/{stats['pool_size']}
• Всего пользователей: {stats['total_active_users']}
• Макс. на соединение: {stats['max_users_per_connection']}

📈 <b>Статистика:</b>
• Всего запросов: {stats['total_requests']}
• Ошибок: {stats['total_errors']} ({stats['error_rate']:.1%})
• Стратегия: {stats['strategy']}

👥 <b>Распределение пользователей:</b>"""
        
        for conn_id, count in stats['user_distribution'].items():
            stats_text += f"\n• {conn_id}: {count} пользователей"
        
        await message.answer(stats_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await message.answer(" Не удалось получить статистику")


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    """Handle /help command."""
    help_text = """🆘 <b>Справка по боту</b>

<b>Основные возможности:</b>
• 📋 Запись на прием к врачу
• 💰 Получение актуальных цен
• 👨‍⚕️ Информация о врачах
• 📅 Поиск свободных слотов
• 🏥 Контакты филиалов

<b>Примеры запросов:</b>
• "Запиши меня к стоматологу"
• "Сколько стоит чистка зубов?"
• "Покажи врачей-хирургов"
• "Есть ли места на завтра?"
• "Где находятся ваши клиники?"

<b>Команды:</b>
/start - главное меню
/help - эта справка
/cancel - отмена текущего действия

💡 <i>Просто опишите, что нужно, естественным языком!</i>
"""
    
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("cancel"))
async def cancel_handler(message: Message, bot: Bot) -> None:
    """Handle /cancel command."""
    user_id = message.from_user.id if message.from_user else 0
    
    logger.info(f"Cancel command from user {user_id}")
    
    # Cancel any active streaming
    try:
        yclients_adapter = get_yclients_adapter()
        connection_pool = await get_connection_pool(yclients_adapter)
        
        stream_state = connection_pool.get_user_stream_state(user_id)
        if stream_state == StreamState.STREAMING:
            await connection_pool.cancel_user_stream(user_id)
            await message.answer("✅ Текущий запрос отменен.")
        else:
            await message.answer("ℹ️ Нет активных запросов для отмены.")
    
    except Exception as e:
        logger.error(f"Error cancelling stream: {e}")
        await message.answer(" Произошла ошибка при отмене.")


@router.message(F.text)
async def text_message_handler(message: Message, bot: Bot) -> None:
    """Handle text messages with Realtime API streaming."""
    if not message.text or not message.from_user:
        return
    
    user_id = message.from_user.id
    user_text = message.text
    
    logger.info(f"Text message from user {user_id}: {user_text[:50]}...")
    
    # Rate limiting check
    if rate_limiter.is_rate_limited(user_id):
        remaining = rate_limiter.get_remaining_requests(user_id)
        await message.answer(
            f"⏳ <b>Превышен лимит запросов</b>\n\n"
            f"Пожалуйста, подождите немного перед следующим запросом.\n"
            f"Осталось запросов: {remaining}/5 в 30 секунд.\n\n"
            f"💡 <i>Это ограничение помогает обеспечить качественную работу для всех пользователей.</i>",
            parse_mode="HTML"
        )
        return
    
    try:
        # Get connection pool
        yclients_adapter = get_yclients_adapter()
        connection_pool = await get_connection_pool(yclients_adapter)
        
        # Send "thinking" placeholder
        thinking_message = await message.answer("🤔 <i>Думаю...</i>", parse_mode="HTML")
        
        # Start streaming through pool
        stream, connection_id = await connection_pool.send_user_message(
            user_id=user_id,
            text=user_text,
            message_id=thinking_message.message_id
        )
        
        logger.info(f"📡 User {user_id} streaming on connection #{connection_id}")
        
        # Set up streaming callbacks
        accumulated_text = ""
        last_sent_text = ""
        
        async def on_delta(delta: str, full_text: str) -> None:
            """Handle text delta updates."""
            nonlocal accumulated_text, last_sent_text
            accumulated_text = full_text
            
            # Throttle message edits
            key = f"{user_id}:{thinking_message.message_id}"
            
            async def edit_message(content: str) -> None:
                try:
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=thinking_message.message_id,
                        text=content,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Failed to edit message: {e}")
            
            await throttler.throttled_edit(key, full_text, edit_message)
        
        async def on_done(final_text: str) -> None:
            """Handle completion."""
            nonlocal accumulated_text, last_sent_text
            accumulated_text = final_text
            
            # Final message edit
            key = f"{user_id}:{thinking_message.message_id}"
            
            async def edit_message(content: str) -> None:
                try:
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=thinking_message.message_id,
                        text=content,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Failed to edit final message: {e}")
            
            await throttler.throttled_edit(key, final_text, edit_message, force=True)
            logger.info(f"Streaming completed for user {user_id}")
        
        async def on_error(error: Exception) -> None:
            """Handle streaming errors."""
            nonlocal accumulated_text, last_sent_text
            logger.error(f"Streaming error for user {user_id}: {error}")
            
            error_text = "😔 <b>Произошла ошибка</b>\n\n"
            
            if "rate limit" in str(error).lower():
                error_text += "Сервис временно перегружен. Попробуйте через минуту."
            elif "timeout" in str(error).lower():
                error_text += "Время ожидания истекло. Попробуйте сформулировать запрос проще."
            else:
                error_text += "Сервис временно недоступен. Попробуем позже или выберем другое время?"
            
            error_text += "\n\n💡 <i>Используйте /help для просмотра примеров запросов.</i>"
            
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=thinking_message.message_id,
                    text=error_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to edit error message: {e}")
        
        # Get the actual client for this user to set callbacks
        client, _ = await connection_pool.get_connection_for_user(user_id)
        
        # Set callbacks
        client.set_stream_callbacks(
            user_id=user_id,
            on_delta=on_delta,
            on_done=on_done,
            on_error=on_error
        )
        
        # Wait for completion with timeout
        timeout_seconds = 30
        start_time = asyncio.get_event_loop().time()
        
        while True:
            state = connection_pool.get_user_stream_state(user_id)
            
            if state in [StreamState.DONE, StreamState.ERROR, StreamState.CANCELLED]:
                break
            
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                logger.warning(f"Stream timeout for user {user_id}")
                await connection_pool.cancel_user_stream(user_id)
                await on_error(Exception("Timeout"))
                break
            
            await asyncio.sleep(0.1)
        
        # Release connection when done
        await connection_pool.release_user_connection(user_id)
    
    except Exception as e:
        logger.error(f"Error handling text message from user {user_id}: {e}")
        
        error_text = " <b>Произошла ошибка</b>\n\n"
        error_text += "Не удалось обработать ваш запрос. Попробуйте еще раз или обратитесь к администратору.\n\n"
        error_text += "💡 <i>Используйте /help для просмотра доступных команд.</i>"
        
        try:
            await message.answer(error_text, parse_mode="HTML")
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")




def get_handlers_router() -> Router:
    """Get configured handlers router."""
    return router
