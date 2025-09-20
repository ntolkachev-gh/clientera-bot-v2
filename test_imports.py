#!/usr/bin/env python3
"""
Тестовый скрипт для проверки импортов и зависимостей.
"""

import sys
import traceback

def test_import(module_name):
    """Тестирует импорт модуля."""
    try:
        __import__(module_name)
        print(f"✅ {module_name} - OK")
        return True
    except Exception as e:
        print(f"❌ {module_name} - FAILED: {e}")
        traceback.print_exc()
        return False

def main():
    print("🧪 Тестирование импортов...")
    
    # Основные зависимости
    modules_to_test = [
        "os",
        "asyncio", 
        "logging",
        "dotenv",
        "aiogram",
        "aiohttp",
        "src",
        "src.integrations",
        "src.integrations.yclients_adapter", 
        "src.realtime",
        "src.realtime.client",
        "src.realtime.events",
        "src.config",
        "src.config.env",
    ]
    
    failed_imports = []
    
    for module in modules_to_test:
        if not test_import(module):
            failed_imports.append(module)
    
    print(f"\n📊 Результаты:")
    print(f"✅ Успешно: {len(modules_to_test) - len(failed_imports)}")
    print(f"❌ Ошибки: {len(failed_imports)}")
    
    if failed_imports:
        print(f"\n❌ Проблемные модули: {failed_imports}")
        return 1
    else:
        print("\n🎉 Все импорты работают!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
