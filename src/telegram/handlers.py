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
    
    # Check if user profile exists, if not - try to get Telegram profile info
    try:
        yclients_adapter = get_yclients_adapter()
        profile_result = await yclients_adapter.get_user_profile(user_id)
        has_profile = profile_result is not None
    except Exception as e:
        logger.warning(f"Error checking user profile {user_id}: {e}")
        has_profile = False

    # If no profile exists, try to get information from Telegram
    if not has_profile:
        try:
            telegram_profile = await yclients_adapter.get_telegram_profile(user_id)
            if telegram_profile.get("success"):
                data = telegram_profile["data"]
                telegram_name = data.get("telegram_first_name") or user_name
                logger.info(f"📱 Got Telegram profile for {user_id}: {telegram_name}")
                
                # Create basic profile with Telegram information
                try:
                    await yclients_adapter.get_or_create_user_profile(
                        telegram_id=user_id,
                        name=telegram_name
                    )
                    logger.info(f"✅ Created profile from Telegram data for {user_id}")
                except Exception as profile_error:
                    logger.error(f"Error creating profile from Telegram: {profile_error}")
            else:
                logger.info(f"❌ Telegram profile not available for {user_id}")
        except Exception as e:
            logger.error(f"Error getting Telegram profile: {e}")
    
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
    
    # Reset user inactivity timer
    try:
        from ..app import reset_user_inactivity_timer_global
        await reset_user_inactivity_timer_global(user_id)
    except Exception as e:
        logger.debug(f"Could not reset inactivity timer for user {user_id}: {e}")
    
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
            """Handle text delta updates with advanced recovery."""
            nonlocal accumulated_text, last_sent_text
            accumulated_text = full_text
            
            # Clean cursor artifacts
            import re
            clean_text = full_text.replace(" <i>_</i>", "").replace(" <i> </i>", "")
            clean_text = re.sub(r'\s*_\s*$', '', clean_text)
            
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
                    logger.debug(f"📝 Updated message for user {user_id} (length: {len(content)})")
                except Exception as e:
                    error_msg = str(e)
                    if "Flood control exceeded" in error_msg or "Too Many Requests" in error_msg:
                        logger.debug(f"⏳ Rate limit for user {user_id}, skipping update")
                    elif "message is not modified" in error_msg:
                        logger.debug(f"📝 Message not modified for user {user_id}")
                    else:
                        logger.warning(f"⚠️ Error updating message for user {user_id}: {e}")
            
            await throttler.throttled_edit(key, clean_text, edit_message)
        
        async def on_done(final_text: str) -> None:
            """Handle completion with guaranteed delivery."""
            nonlocal accumulated_text, last_sent_text
            accumulated_text = final_text
            
            # Clean final text
            import re
            clean_final = final_text.replace(" <i>_</i>", "").replace(" <i> </i>", "").replace("_", "").strip()
            
            # Final message edit with retry logic
            async def edit_message(content: str) -> None:
                try:
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=thinking_message.message_id,
                        text=content,
                        parse_mode="HTML"
                    )
                    logger.info(f"✅ Final message delivered to user {user_id} (length: {len(content)})")
                except Exception as e:
                    error_msg = str(e)
                    if "Flood control exceeded" in error_msg or "Too Many Requests" in error_msg:
                        logger.warning(f"⏳ Rate limit in finalization for user {user_id}, retrying...")
                        await asyncio.sleep(5)
                        try:
                            await bot.edit_message_text(
                                chat_id=message.chat.id,
                                message_id=thinking_message.message_id,
                                text=content,
                                parse_mode="HTML"
                            )
                            logger.info(f"Final message delivered after delay for user {user_id}")
                        except Exception as retry_e:
                            logger.error(f"Retry finalization error for user {user_id}: {retry_e}")
                    else:
                        logger.error(f"Failed to edit final message for user {user_id}: {e}")
            
            # Force final update without throttling
            if clean_final.strip():
                await edit_message(clean_final)
                last_sent_text = clean_final
            
            logger.info(f"✅ Streaming completed for user {user_id}")
        
        async def on_error(error: Exception) -> None:
            """Handle streaming errors with smart recovery."""
            nonlocal accumulated_text, last_sent_text
            logger.error(f"❌ Stream error for user {user_id}: {error}")
            
            error_str = str(error).lower()
            
            # Smart error handling based on error type
            if "quota" in error_str or "limit" in error_str or "insufficient" in error_str:
                error_text = """💳 <b>Временные технические проблемы</b>

AI-консультант временно недоступен из-за превышения лимитов API.

🔧 <b>Что делать:</b>
• Попробуйте позже через 10-15 минут
• Или обратитесь напрямую по телефону:

📞 <b>+7 (495) 123-45-67</b>

Извините за неудобства! 😔"""
            elif "timeout" in error_str:
                error_text = """⏰ <b>Извините, AI-консультант не отвечает</b>

Возможные причины:
• Высокая нагрузка на сервис
• Технические проблемы с AI
• Сложный запрос требует больше времени

<b>Что делать:</b>
• Попробуйте задать вопрос проще
• Или обратитесь напрямую:
📞 +7 (495) 123-45-67"""
            elif "rate limit" in error_str:
                error_text = """⏳ <b>Превышен лимит запросов</b>

Сервис временно перегружен.
Попробуйте через минуту.

💡 <i>Это ограничение помогает обеспечить качественную работу для всех пользователей.</i>"""
            else:
                error_text = """😔 <b>Произошла ошибка</b>

Не удалось обработать ваш запрос.
Попробуйте еще раз или обратитесь по телефону:
📞 +7 (495) 123-45-67

💡 <i>Используйте /help для примеров запросов.</i>"""
            
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=thinking_message.message_id,
                    text=error_text,
                    parse_mode="HTML"
                )
                logger.info(f"📤 Sent error message to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send error message to user {user_id}: {e}")
        
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
