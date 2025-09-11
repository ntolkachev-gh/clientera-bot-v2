#!/usr/bin/env python3
"""
Тестовый скрипт для проверки кеширования врачей.
"""

import asyncio
import time
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Импортируем классы из dental_bot
from dental_bot import YClientsIntegration, doctors_cache

async def test_doctors_caching():
    """Тестирует кеширование врачей."""
    print("🧪 Тестирование кеширования врачей...")
    
    try:
        # Инициализируем YClients интеграцию
        yclients = YClientsIntegration()
        print("✅ YClients интеграция инициализирована")
        
        # Очищаем кеш для чистого теста
        yclients.clear_doctors_cache()
        print("🗑️ Кеш очищен")
        
        # Первый запрос - должен идти в API
        print("\n📋 Первый запрос (из API)...")
        start_time = time.time()
        result1 = await yclients.get_doctors()
        end_time = time.time()
        
        if result1.get('doctors'):
            print(f"Получено {len(result1['doctors'])} врачей за {end_time - start_time:.2f} секунд")
            print("Первые 2 врача:")
            for i, doctor in enumerate(result1['doctors'][:2], 1):
                print(f"  {i}. {doctor['name']} - {doctor['position']}")
        
        # Проверяем статистику кеша
        cache_stats = yclients.get_cache_stats()
        print(f"\n💾 Статистика кеша: {cache_stats}")
        
        # Второй запрос - должен идти из кеша
        print("\n📋 Второй запрос (из кеша)...")
        start_time = time.time()
        result2 = await yclients.get_doctors()
        end_time = time.time()
        
        if result2.get('doctors'):
            print(f"Получено {len(result2['doctors'])} врачей за {end_time - start_time:.2f} секунд")
        
        # Проверяем, что данные одинаковые
        if result1 == result2:
            print("✅ Данные из кеша идентичны данным из API")
        else:
            print(" Данные из кеша отличаются от данных из API")
        
        # Тестируем фильтрацию
        print("\n🔍 Тестируем фильтрацию по специализации...")
        start_time = time.time()
        filtered_result = await yclients.get_doctors("терапевт")
        end_time = time.time()
        
        if filtered_result.get('doctors'):
            print(f"Найдено {len(filtered_result['doctors'])} терапевтов за {end_time - start_time:.2f} секунд")
            for i, doctor in enumerate(filtered_result['doctors'], 1):
                print(f"  {i}. {doctor['name']} - {doctor['position']}")
                if 'specialization' in doctor:
                    print(f"     Специализация: {doctor['specialization']}")
        else:
            print("⚠️ Терапевты не найдены")
        
        # Финальная статистика кеша
        final_cache_stats = yclients.get_cache_stats()
        print(f"\n💾 Финальная статистика кеша: {final_cache_stats}")
        
        print("\n✅ Тестирование кеширования завершено!")
        
    except Exception as e:
        print(f" Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_doctors_caching())
