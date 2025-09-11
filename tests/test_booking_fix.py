#!/usr/bin/env python3
"""
Тест исправленного потока записи на прием.
Проверяет обработку ошибки 422 при создании клиента.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integrations.yclients_adapter import get_yclients_adapter
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_existing_client_booking():
    """Тестируем запись существующего клиента (ошибка 422)."""
    logger.info("🧪 Тестируем запись существующего клиента...")
    
    adapter = get_yclients_adapter()
    
    # Данные для теста (клиент с номером из лога)
    test_data = {
        "patient_name": "Олег",
        "phone": "+79291284250",
        "service": "Первичная консультация эндодонтиста", 
        "doctor": "Магомед Расулов",
        "datetime": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    }
    
    try:
        result = await adapter.book_appointment(**test_data)
        
        if result.get('success'):
            logger.info("✅ Запись успешно создана!")
            logger.info(f"📝 Детали: {result}")
        else:
            logger.error(f"❌ Ошибка записи: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"💥 Исключение при записи: {e}")
        return False
    
    return True


async def test_new_client_booking():
    """Тестируем запись нового клиента."""
    logger.info("🧪 Тестируем запись нового клиента...")
    
    adapter = get_yclients_adapter()
    
    # Данные для теста (новый клиент)
    test_data = {
        "patient_name": "Тестовый Пациент",
        "phone": "+79999999999",  # Заведомо несуществующий номер
        "service": "Консультация стоматолога-терапевта",
        "doctor": "Магомед Расулов", 
        "datetime": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
    }
    
    try:
        result = await adapter.book_appointment(**test_data)
        
        if result.get('success'):
            logger.info("✅ Запись нового клиента успешно создана!")
            logger.info(f"📝 Детали: {result}")
        else:
            logger.error(f"❌ Ошибка записи нового клиента: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"💥 Исключение при записи нового клиента: {e}")
        return False
    
    return True


async def test_client_search():
    """Тестируем поиск клиентов."""
    logger.info("🧪 Тестируем поиск клиентов...")
    
    adapter = get_yclients_adapter()
    
    try:
        # Тестируем поиск существующего клиента
        phone = "+79291284250"
        result = await adapter.service.api.find_or_create_client("Олег", phone)
        
        if result.get('success'):
            logger.info("✅ Клиент найден!")
            logger.info(f"📱 Данные клиента: {result['data']}")
        else:
            logger.error(f"❌ Ошибка поиска клиента: {result}")
            return False
            
    except Exception as e:
        logger.error(f"💥 Исключение при поиске клиента: {e}")
        return False
    
    return True


async def main():
    """Основная функция тестирования."""
    logger.info("🚀 Запуск тестов исправленного потока записи...")
    
    # Проверяем переменные окружения
    if not os.getenv('YCLIENTS_TOKEN'):
        logger.error("❌ Не установлен YCLIENTS_TOKEN в переменных окружения")
        return
        
    if not os.getenv('YCLIENTS_COMPANY_ID'):
        logger.error("❌ Не установлен YCLIENTS_COMPANY_ID в переменных окружения")
        return
    
    tests = [
        ("Поиск клиентов", test_client_search),
        ("Запись существующего клиента", test_existing_client_booking),
        ("Запись нового клиента", test_new_client_booking),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"🧪 Тест: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            success = await test_func()
            results.append((test_name, success))
            
            if success:
                logger.info(f"✅ {test_name}: УСПЕШНО")
            else:
                logger.error(f"❌ {test_name}: НЕУДАЧНО")
                
        except Exception as e:
            logger.error(f"💥 {test_name}: ИСКЛЮЧЕНИЕ - {e}")
            results.append((test_name, False))
        
        # Пауза между тестами
        await asyncio.sleep(1)
    
    # Итоговые результаты
    logger.info(f"\n{'='*50}")
    logger.info("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    logger.info(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ УСПЕШНО" if success else "❌ НЕУДАЧНО"
        logger.info(f"{status}: {test_name}")
        if success:
            passed += 1
    
    logger.info(f"\n📈 Результат: {passed}/{total} тестов прошли успешно")
    
    if passed == total:
        logger.info("🎉 Все тесты прошли успешно!")
    else:
        logger.warning(f"⚠️ {total - passed} тестов не прошли")


if __name__ == "__main__":
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())
