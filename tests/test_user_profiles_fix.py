#!/usr/bin/env python3
"""
Тест исправленной системы профилей пользователей.
"""

import asyncio
import logging
import os
import sys

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integrations.user_profiles import get_profile_manager
from src.integrations.yclients_adapter import get_yclients_adapter
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_profile_manager_initialization():
    """Тестируем инициализацию менеджера профилей."""
    logger.info("🧪 Тест инициализации менеджера профилей...")
    
    try:
        manager = get_profile_manager()
        
        # Проверяем что API инициализирован с user_token
        if manager.api.user_token:
            logger.info(f"✅ Менеджер профилей инициализирован с user_token")
        else:
            logger.error("❌ Менеджер профилей БЕЗ user_token")
            return False
            
        logger.info(f"📊 Статистика профилей: {manager.get_stats()}")
        return True
        
    except Exception as e:
        logger.error(f"💥 Ошибка инициализации: {e}")
        return False


async def test_register_user_via_adapter():
    """Тестируем регистрацию пользователя через адаптер."""
    logger.info("🧪 Тест регистрации пользователя через адаптер...")
    
    try:
        adapter = get_yclients_adapter()
        
        # Тестовые данные
        test_data = {
            "telegram_id": 123456789,
            "name": "Тестовый Пользователь",
            "phone": "+79999999999"
        }
        
        result = await adapter.register_user(**test_data)
        
        if result.get('success'):
            logger.info("✅ Пользователь успешно зарегистрирован!")
            logger.info(f"📝 Профиль: {result['profile']}")
            return True
        else:
            logger.error(f"❌ Ошибка регистрации: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"💥 Исключение при регистрации: {e}")
        return False


async def test_get_user_profile():
    """Тестируем получение профиля пользователя."""
    logger.info("🧪 Тест получения профиля пользователя...")
    
    try:
        adapter = get_yclients_adapter()
        
        # Пытаемся получить профиль тестового пользователя
        result = await adapter.get_user_profile(123456789)
        
        if result:
            logger.info("✅ Профиль найден!")
            logger.info(f"📝 Данные профиля: {result}")
            return True
        else:
            logger.info("ℹ️ Профиль не найден (это нормально для нового пользователя)")
            return True
            
    except Exception as e:
        logger.error(f"💥 Исключение при получении профиля: {e}")
        return False


async def test_yclients_api_connection():
    """Тестируем подключение к YClients API."""
    logger.info("🧪 Тест подключения к YClients API...")
    
    try:
        manager = get_profile_manager()
        
        # Проверяем что можем выполнить простой запрос
        # Попробуем получить список услуг (не требует user_token)
        services_result = await manager.service.get_services()
        
        if services_result.get('success'):
            services = services_result.get('services', [])
            logger.info(f"✅ Подключение к YClients работает, получено {len(services)} услуг")
            return True
        else:
            logger.error(f"❌ Ошибка получения услуг: {services_result}")
            return False
            
    except Exception as e:
        logger.error(f"💥 Исключение при тестировании API: {e}")
        return False


async def main():
    """Основная функция тестирования."""
    logger.info("🚀 Запуск тестов исправленной системы профилей...")
    
    # Проверяем переменные окружения
    required_vars = ['YCLIENTS_TOKEN', 'YCLIENTS_COMPANY_ID', 'YCLIENTS_USER_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Отсутствуют переменные окружения: {missing_vars}")
        return
    
    tests = [
        ("Инициализация менеджера профилей", test_profile_manager_initialization),
        ("Подключение к YClients API", test_yclients_api_connection),
        ("Получение профиля пользователя", test_get_user_profile),
        ("Регистрация пользователя", test_register_user_via_adapter),
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
