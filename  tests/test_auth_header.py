#!/usr/bin/env python3
"""
Тестовый скрипт для проверки формирования заголовка Authorization.
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def test_auth_header():
    """Тестирует формирование заголовка Authorization."""
    print("🧪 Тестирование формирования заголовка Authorization...")
    
    token = os.getenv("YCLIENTS_TOKEN")
    user_token = os.getenv("YCLIENTS_USER_TOKEN")
    
    print(f"YCLIENTS_TOKEN: {token}")
    print(f"YCLIENTS_USER_TOKEN: {user_token}")
    
    if token and user_token:
        auth_header = f'Bearer {token}, User {user_token}'
        print(f"\n✅ Заголовок Authorization будет:")
        print(f"'Authorization: {auth_header}'")
        
        # Сравниваем с ожидаемым
        expected = 'Bearer r9ybfmkgm4u8nau7ehx4, User 5a647b231213538f72f76e09f539a9c9'
        if auth_header == expected:
            print("✅ Заголовок сформирован правильно!")
        else:
            print(" Заголовок не соответствует ожидаемому:")
            print(f"Ожидается: 'Authorization: {expected}'")
    else:
        print(" Не все токены настроены в .env файле")
        if not token:
            print("  - Отсутствует YCLIENTS_TOKEN")
        if not user_token:
            print("  - Отсутствует YCLIENTS_USER_TOKEN")

if __name__ == "__main__":
    test_auth_header()
