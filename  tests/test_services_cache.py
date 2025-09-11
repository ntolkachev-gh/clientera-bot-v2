#!/usr/bin/env python3
"""
Тестовый скрипт для проверки кеширования услуг.
"""

import asyncio
import time
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Импортируем классы из dental_bot
from dental_bot import YClientsIntegration, services_cache

async def test_services_caching():
    """Тестирует кеширование услуг."""
    print("🧪 Тестирование кеширования услуг...")
    
    try:
        # Инициализируем YClients интеграцию
        yclients = YClientsIntegration()
        print("✅ YClients интеграция инициализирована")
        
        # Очищаем кеш для чистого теста
        yclients.clear_services_cache()
        print("🗑️ Кеш услуг очищен")
        
        # Первый запрос - должен идти в API
        print("\n📋 Первый запрос услуг (из API)...")
        start_time = time.time()
        result1 = await yclients.get_services()
        end_time = time.time()
        
        if result1.get('services'):
            print(f"Получено {len(result1['services'])} услуг за {end_time - start_time:.2f} секунд")
            print("Первые 3 услуги:")
            for i, service in enumerate(result1['services'][:3], 1):
                price_info = f"Цена: {service['price']}" if service.get('price') else "Цена: не указана"
                duration_info = f"Длительность: {service['duration']}" if service.get('duration') else ""
                print(f"  {i}. {service['name']} - {price_info}, {duration_info}")
                if service.get('description'):
                    print(f"     Описание: {service['description'][:100]}...")
        
        # Проверяем статистику кеша
        cache_stats = yclients.get_services_cache_stats()
        print(f"\n💾 Статистика кеша услуг: {cache_stats}")
        
        # Второй запрос - должен идти из кеша
        print("\n📋 Второй запрос услуг (из кеша)...")
        start_time = time.time()
        result2 = await yclients.get_services()
        end_time = time.time()
        
        if result2.get('services'):
            print(f"Получено {len(result2['services'])} услуг за {end_time - start_time:.2f} секунд")
        
        # Проверяем, что данные одинаковые
        if result1 == result2:
            print("✅ Данные из кеша идентичны данным из API")
        else:
            print(" Данные из кеша отличаются от данных из API")
        
        # Тестируем фильтрацию
        print("\n🔍 Тестируем фильтрацию по категории...")
        start_time = time.time()
        filtered_result = await yclients.get_services("терапия")
        end_time = time.time()
        
        if filtered_result.get('services'):
            print(f"Найдено {len(filtered_result['services'])} услуг терапии за {end_time - start_time:.2f} секунд")
            for i, service in enumerate(filtered_result['services'][:3], 1):
                print(f"  {i}. {service['name']} - {service['price']}")
        else:
            print("⚠️ Услуги терапии не найдены")
        
        # Тестируем общую статистику всех кешей
        print("\n📊 Общая статистика всех кешей:")
        all_stats = yclients.get_all_cache_stats()
        for cache_name, stats in all_stats.items():
            print(f"  {cache_name}: {stats}")
        
        print("\n✅ Тестирование кеширования услуг завершено!")
        
    except Exception as e:
        print(f" Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_services_caching())
