#!/usr/bin/env python3
"""
Тест улучшенной функции search_slots
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Добавляем путь к src для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from integrations.yclients_adapter import get_yclients_adapter
from utils.logger import get_logger

logger = get_logger(__name__)

async def test_search_slots():
    """Тестируем новую реализацию search_slots"""
    
    # Получаем адаптер
    adapter = get_yclients_adapter()
    
    # Получаем список врачей для тестирования
    print("🔍 Получаем список врачей...")
    doctors = await adapter.list_doctors()
    
    if not doctors:
        print("❌ Врачи не найдены")
        return
    
    # Берем первого врача для тестирования
    test_doctor = doctors[0]
    doctor_id = test_doctor['id']
    doctor_name = test_doctor['name']
    
    print(f"👨‍⚕️ Тестируем с врачом: {doctor_name} (ID: {doctor_id})")
    
    # Тестируем поиск слотов на завтрашний день
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"📅 Ищем слоты на дату: {tomorrow}")
    
    # Вызываем новую функцию search_slots
    slots = await adapter.search_slots(doctor_id, tomorrow)
    
    print(f"🎯 Найдено слотов: {len(slots)}")
    
    # Выводим первые несколько слотов
    for i, slot in enumerate(slots[:5]):  # Показываем только первые 5
        print(f"   {i+1}. {slot['time']} - {slot['doctor']} (доступен: {slot['available']})")
    
    if len(slots) > 5:
        print(f"   ... и еще {len(slots) - 5} слотов")
    
    return slots

async def main():
    """Главная функция теста"""
    try:
        print("🚀 Тестируем улучшенную функцию search_slots")
        print("=" * 50)
        
        slots = await test_search_slots()
        
        print("\n" + "=" * 50)
        if slots:
            print("✅ Тест успешно завершен!")
            print(f"📊 Результат: найдено {len(slots)} доступных слотов")
        else:
            print("⚠️ Слоты не найдены (возможно, врач не работает завтра)")
            
    except Exception as e:
        print(f"❌ Ошибка во время тестирования: {e}")
        logger.error(f"Test error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
