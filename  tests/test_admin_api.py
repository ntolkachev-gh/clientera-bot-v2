#!/usr/bin/env python3
"""
Тестовый скрипт для проверки админ API.
"""

import asyncio
import aiohttp
import json

async def test_admin_api(base_url="http://localhost:8080"):
    """Тестирует админ API."""
    print("🧪 Тестирование админ API...")
    print(f"🌐 Базовый URL: {base_url}")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Тест 1: Проверка здоровья
            print("\n1️⃣ Проверка здоровья сервера...")
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"Сервер здоров: {data}")
                else:
                    print(f" Ошибка здоровья: {response.status}")
            
            # Тест 2: Получение статистики кешей
            print("\n2️⃣ Получение статистики кешей...")
            async with session.get(f"{base_url}/cache/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"Статистика получена:")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    print(f" Ошибка получения статистики: {response.status}")
            
            # Тест 3: Очистка кешей
            print("\n3️⃣ Очистка кешей...")
            async with session.post(f"{base_url}/cache/clear") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"Кеши очищены: {data['message']}")
                else:
                    print(f" Ошибка очистки кешей: {response.status}")
            
            # Тест 4: Обновление кешей
            print("\n4️⃣ Обновление кешей...")
            async with session.post(f"{base_url}/cache/refresh") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"Кеши обновлены: {data['message']}")
                else:
                    print(f" Ошибка обновления кешей: {response.status}")
            
            # Тест 5: Повторное получение статистики
            print("\n5️⃣ Повторное получение статистики...")
            async with session.get(f"{base_url}/cache/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"Обновленная статистика:")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    print(f" Ошибка получения статистики: {response.status}")
            
            print(f"\n🎉 Тестирование завершено!")
            print(f"🌐 Откройте {base_url} в браузере для веб-интерфейса")
            
        except aiohttp.ClientConnectorError:
            print(f" Не удалось подключиться к {base_url}")
            print("💡 Убедитесь, что бот запущен и админ-сервер работает")
        except Exception as e:
            print(f" Ошибка при тестировании: {e}")

def main():
    """Главная функция."""
    import sys
    
    base_url = "http://localhost:8080"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    asyncio.run(test_admin_api(base_url))

if __name__ == "__main__":
    main()
