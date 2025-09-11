#!/usr/bin/env python3
"""
Тест для проверки fallback генерации слотов
"""

import asyncio
import os
from dotenv import load_dotenv
from src.integrations.yclients_adapter import YClientsAdapter

# Загружаем .env
load_dotenv()

async def test_slots_fallback():
    """Тестирует генерацию слотов при отсутствии свободных слотов"""
    
    print("🧪 Тестируем fallback генерацию слотов...")
    
    # Создаем адаптер
    adapter = YClientsAdapter()
    
    # Тестируем генерацию слотов
    test_date = "2025-09-11"
    doctor_id = 123
    service_id = 456
    doctor_name = "Тестовый врач"
    
    print(f"📅 Генерируем слоты на {test_date}")
    print(f"👨‍⚕️ Врач: {doctor_name} (ID: {doctor_id})")
    print(f"🦷 Услуга ID: {service_id}")
    print(f"⏰ Время работы: {adapter.work_start_hour}:00-{adapter.work_end_hour}:00")
    print(f"⏱️ Интервал: {adapter.slot_interval_minutes} минут")
    
    # Генерируем слоты
    slots = adapter._generate_day_slots(test_date, doctor_id, service_id, doctor_name)
    
    print(f"\n✅ Сгенерировано {len(slots)} слотов:")
    print("-" * 50)
    
    # Показываем первые 10 слотов
    for i, slot in enumerate(slots[:10]):
        print(f"{i+1:2d}. {slot['time']} - {slot['doctor']} (ID: {slot['doctor_id']})")
    
    if len(slots) > 10:
        print(f"... и еще {len(slots) - 10} слотов")
    
    print("-" * 50)
    
    # Проверяем структуру слотов
    if slots:
        sample_slot = slots[0]
        required_fields = ['datetime', 'date', 'time', 'doctor', 'doctor_id', 'service_id', 'available', 'generated']
        
        print("\n🔍 Проверяем структуру слотов:")
        for field in required_fields:
            if field in sample_slot:
                print(f"  ✅ {field}: {sample_slot[field]}")
            else:
                print(f"  ❌ {field}: ОТСУТСТВУЕТ")
    
    print(f"\n🎉 Тест завершен! Сгенерировано {len(slots)} слотов")

async def test_different_configurations():
    """Тестирует разные конфигурации времени работы"""
    
    print("\n🧪 Тестируем разные конфигурации...")
    
    configurations = [
        {"start": 9, "end": 18, "interval": 30, "name": "Стандартная клиника"},
        {"start": 8, "end": 20, "interval": 15, "name": "Расширенный график"},
        {"start": 10, "end": 16, "interval": 60, "name": "Короткий день"},
    ]
    
    for config in configurations:
        print(f"\n📋 {config['name']}: {config['start']}:00-{config['end']}:00, интервал {config['interval']}мин")
        
        # Временно устанавливаем конфигурацию
        os.environ['CLINIC_START_HOUR'] = str(config['start'])
        os.environ['CLINIC_END_HOUR'] = str(config['end'])
        os.environ['SLOT_INTERVAL_MINUTES'] = str(config['interval'])
        
        # Создаем новый адаптер с новой конфигурацией
        adapter = YClientsAdapter()
        
        # Генерируем слоты
        slots = adapter._generate_day_slots("2025-09-11", 123, 456, "Тестовый врач")
        
        print(f"  📊 Слотов: {len(slots)}")
        print(f"  ⏰ Первый слот: {slots[0]['time'] if slots else 'Нет'}")
        print(f"  ⏰ Последний слот: {slots[-1]['time'] if slots else 'Нет'}")

async def main():
    """Главная функция тестирования"""
    try:
        await test_slots_fallback()
        await test_different_configurations()
        print("\n🎉 Все тесты завершены успешно!")
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")

if __name__ == "__main__":
    asyncio.run(main())
