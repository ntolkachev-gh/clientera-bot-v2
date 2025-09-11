#!/usr/bin/env python3
"""
Простой тест для проверки очищенных данных врачей.
"""

import asyncio
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Импортируем класс из dental_bot
from dental_bot import YClientsIntegration

async def test_clean_doctors_data():
    """Тестирует получение очищенных данных врачей."""
    print("🧪 Тестирование очищенных данных врачей...")
    
    try:
        # Инициализируем YClients интеграцию
        yclients = YClientsIntegration()
        print("✅ YClients интеграция инициализирована")
        
        # Получаем врачей
        print("\n📋 Получаем врачей...")
        result = await yclients.get_doctors()
        
        if result.get('doctors'):
            print(f"Получено {len(result['doctors'])} врачей:")
            print("\n" + "="*60)
            
            for i, doctor in enumerate(result['doctors'], 1):
                print(f"\n{i}. {doctor['name']}")
                print(f"   Должность: {doctor['position']}")
                
                if 'specialization' in doctor:
                    print(f"   Специализация: {doctor['specialization']}")
                
                if 'description' in doctor:
                    print(f"   Описание: {doctor['description']}")
                
                print("-" * 40)
        else:
            print(" Врачи не найдены")
            print(f"Ответ: {result}")
        
        print("\n✅ Тестирование завершено!")
        
    except Exception as e:
        print(f" Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(test_clean_doctors_data())
