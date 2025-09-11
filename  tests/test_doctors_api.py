#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы получения врачей из YClients API.
"""

import asyncio
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Импортируем классы из dental_bot
from dental_bot import YClientsIntegration

async def test_doctors_api():
    """Тестирует получение врачей через YClients API."""
    print("🧪 Тестирование получения врачей из YClients API...")
    
    try:
        # Проверяем наличие необходимых переменных окружения
        required_vars = ['YCLIENTS_TOKEN', 'YCLIENTS_COMPANY_ID']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f" Отсутствуют переменные окружения: {', '.join(missing_vars)}")
            print("Добавьте их в файл .env:")
            for var in missing_vars:
                print(f"  {var}=your_value_here")
            return
        
        # Инициализируем YClients интеграцию
        yclients = YClientsIntegration()
        print("✅ YClients интеграция инициализирована")
        
        # Тестируем получение всех врачей
        print("\n📋 Получаем всех врачей...")
        all_doctors = await yclients.get_doctors()
        
        if all_doctors.get('doctors'):
            print(f"Получено {len(all_doctors['doctors'])} врачей:")
            for i, doctor in enumerate(all_doctors['doctors'], 1):
                print(f"  {i}. {doctor['name']} - {doctor['position']}")
                if 'description' in doctor:
                    print(f"     Описание: {doctor['description'][:100]}...")
        else:
            print("⚠️ Врачи не найдены или произошла ошибка")
            print(f"Ответ: {all_doctors}")
        
        # Тестируем фильтрацию по специализации
        print(f"\n🔍 Тестируем фильтрацию по специализации 'терапевт'...")
        filtered_doctors = await yclients.get_doctors("терапевт")
        
        if filtered_doctors.get('doctors'):
            print(f"Найдено {len(filtered_doctors['doctors'])} терапевтов:")
            for i, doctor in enumerate(filtered_doctors['doctors'], 1):
                print(f"  {i}. {doctor['name']} - {doctor['position']}")
        else:
            print("⚠️ Терапевты не найдены")
            print(f"Ответ: {filtered_doctors}")
        
        print("\n✅ Тестирование завершено!")
        
    except Exception as e:
        print(f" Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_doctors_api())
