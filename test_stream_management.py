#!/usr/bin/env python3
"""
Тестовый скрипт для проверки управления стримами в dental_bot.
"""

import asyncio
import logging
import time
from dental_bot import DentalRealtimeClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_stream_management():
    """Тестирование управления стримами."""
    client = DentalRealtimeClient()
    
    try:
        # Подключаемся к OpenAI
        logger.info("🔌 Подключаемся к OpenAI Realtime API...")
        await client.connect()
        await asyncio.sleep(1)
        
        # Симулируем несколько пользователей
        test_users = [
            (1001, "Привет, какие услуги вы предоставляете?", 1),
            (1002, "Хочу записаться на прием", 2),
            (1001, "Сколько стоит консультация?", 3),  # Тот же пользователь, новое сообщение
        ]
        
        for user_id, message, msg_id in test_users:
            logger.info(f"\n{'='*60}")
            logger.info(f"📤 Отправляем сообщение от пользователя {user_id}: '{message}'")
            
            # Проверяем статистику до отправки
            stats_before = client.get_stream_stats()
            logger.info(f"📊 Статистика ДО отправки:")
            logger.info(f"   Активных стримов: {stats_before['active_streams']}")
            logger.info(f"   Незавершенных: {stats_before['uncompleted_stream_count']}")
            logger.info(f"   Завершенных: {stats_before['completed_stream_count']}")
            
            if stats_before['stream_details']:
                logger.info("   Детали стримов:")
                for uid, details in stats_before['stream_details'].items():
                    logger.info(f"     User {uid}: age_created={details['age_created']}s, "
                              f"completed={details['completed']}, "
                              f"has_response_id={details['has_openai_response_id']}")
            
            # Отправляем сообщение
            await client.send_user_message(user_id, message, msg_id)
            
            # Ждем немного для обработки
            await asyncio.sleep(3)
            
            # Проверяем статистику после отправки
            stats_after = client.get_stream_stats()
            logger.info(f"\n📊 Статистика ПОСЛЕ отправки и ожидания:")
            logger.info(f"   Активных стримов: {stats_after['active_streams']}")
            logger.info(f"   Незавершенных: {stats_after['uncompleted_stream_count']}")
            logger.info(f"   Завершенных: {stats_after['completed_stream_count']}")
            
            if stats_after['stream_details']:
                logger.info("   Детали стримов:")
                for uid, details in stats_after['stream_details'].items():
                    logger.info(f"     User {uid}: age_created={details['age_created']}s, "
                              f"completed={details['completed']}, "
                              f"has_response_id={details['has_openai_response_id']}, "
                              f"response_id={details['openai_response_id']}, "
                              f"text_len={details['text_length']}")
        
        # Финальная статистика
        await asyncio.sleep(5)
        final_stats = client.get_stream_stats()
        logger.info(f"\n{'='*60}")
        logger.info("📊 ФИНАЛЬНАЯ СТАТИСТИКА:")
        logger.info(f"   Активных стримов: {final_stats['active_streams']}")
        logger.info(f"   Незавершенных: {final_stats['uncompleted_stream_count']}")
        logger.info(f"   Завершенных: {final_stats['completed_stream_count']}")
        logger.info(f"   Общая стоимость: ${final_stats['total_cost']}")
        
        if final_stats['stream_details']:
            logger.info("\n   Детальная информация о стримах:")
            for uid, details in final_stats['stream_details'].items():
                logger.info(f"   User {uid}:")
                logger.info(f"     - Возраст стрима: {details['age_created']}s")
                logger.info(f"     - Завершен: {details['completed']}")
                logger.info(f"     - Финализирован: {details['finalized']}")
                logger.info(f"     - OpenAI Response ID: {details['openai_response_id']}")
                logger.info(f"     - Длина текста: {details['text_length']} символов")
        
        # Тест очистки старых стримов
        logger.info(f"\n{'='*60}")
        logger.info("🧹 Тестируем очистку старых стримов...")
        cleaned = await client.cleanup_stale_streams()
        logger.info(f"   Очищено стримов: {cleaned}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в тесте: {e}", exc_info=True)
    
    finally:
        # Закрываем соединение
        if client.websocket:
            await client.websocket.close()
        logger.info("\n✅ Тест завершен")

if __name__ == "__main__":
    asyncio.run(test_stream_management())
