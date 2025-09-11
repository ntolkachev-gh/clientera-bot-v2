#!/usr/bin/env python3
"""
Отладка YClients API для услуг
"""

import asyncio
import json
import logging
import os
from dotenv import load_dotenv
import aiohttp

# Загружаем .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def debug_services_endpoints():
    """Отладка различных endpoints для услуг"""
    
    token = os.getenv("YCLIENTS_TOKEN")
    company_id = os.getenv("YCLIENTS_COMPANY_ID")
    login = os.getenv("YCLIENTS_LOGIN")
    password = os.getenv("YCLIENTS_PASSWORD")
    
    if not all([token, company_id]):
        logger.error(" YClients настройки не найдены!")
        return
    
    base_url = "https://api.yclients.com/api/v1"
    headers = {
        'Accept': 'application/vnd.yclients.v2+json',
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Получаем user token
    user_token = None
    if login and password:
        import requests
        try:
            response = requests.post(f"{base_url}/auth", headers=headers, json={
                "login": login,
                "password": password
            })
            result = response.json()
            if result.get('success') and result.get('data', {}).get('user_token'):
                user_token = result['data']['user_token']
                headers['Authorization'] = f'Bearer {token}, User {user_token}'
                logger.info("✅ User token получен")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить user token: {e}")
    
    async with aiohttp.ClientSession() as session:
        
        # 1. Пробуем получить категории услуг
        logger.info("🔍 1. Получаем категории услуг...")
        try:
            url = f"{base_url}/service_categories/{company_id}"
            async with session.get(url, headers=headers) as response:
                result = await response.json()
                logger.info(f"📥 Категории ({response.status}): {json.dumps(result, indent=2, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f" Ошибка получения категорий: {e}")
        
        # 2. Пробуем создать категорию услуг
        logger.info("\n🔍 2. Пробуем создать категорию услуг...")
        try:
            url = f"{base_url}/service_categories/{company_id}"
            category_data = {
                "title": "Стоматологические услуги",
                "weight": 1
            }
            async with session.post(url, headers=headers, json=category_data) as response:
                result = await response.json()
                logger.info(f"📥 Создание категории ({response.status}): {json.dumps(result, indent=2, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f" Ошибка создания категории: {e}")
        
        # 3. Пробуем разные endpoints для создания услуг
        service_data = {
            "title": "Тестовая консультация",
            "category_id": 0,
            "price_min": 1500,
            "price_max": 1500,
            "duration": 30,
            "description": "Тестовая услуга",
            "active": 1
        }
        
        endpoints_to_try = [
            f"services/{company_id}",
            f"service/{company_id}",
            f"company/{company_id}/services",
            f"company/{company_id}/service"
        ]
        
        for endpoint in endpoints_to_try:
            logger.info(f"\n🔍 3. Пробуем создать услугу через: {endpoint}")
            try:
                url = f"{base_url}/{endpoint}"
                async with session.post(url, headers=headers, json=service_data) as response:
                    result = await response.json()
                    logger.info(f"📥 Создание услуги ({response.status}): {json.dumps(result, indent=2, ensure_ascii=False)}")
                    if response.status == 200 or response.status == 201:
                        logger.info(f"Успешно! Используем endpoint: {endpoint}")
                        break
            except Exception as e:
                logger.error(f" Ошибка создания услуги через {endpoint}: {e}")
        
        # 4. Пробуем получить информацию о компании
        logger.info(f"\n🔍 4. Получаем информацию о компании...")
        try:
            url = f"{base_url}/company/{company_id}"
            async with session.get(url, headers=headers) as response:
                result = await response.json()
                logger.info(f"📥 Информация о компании ({response.status}): {json.dumps(result, indent=2, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f" Ошибка получения информации о компании: {e}")

if __name__ == "__main__":
    asyncio.run(debug_services_endpoints())
