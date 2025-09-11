#!/usr/bin/env python3
"""
Простой скрипт для тестирования подключения к YClients API
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

async def test_yclients_api():
    """Тестирует подключение к YClients API"""
    
    token = os.getenv("YCLIENTS_TOKEN")
    company_id = os.getenv("YCLIENTS_COMPANY_ID")
    
    if not all([token, company_id]):
        logger.error(" YClients настройки не найдены! Проверьте .env файл")
        return
    
    base_url = "https://api.yclients.com/api/v1"
    headers = {
        'Accept': 'application/vnd.yclients.v2+json',
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    logger.info(f"🔗 Тестируем подключение к YClients API...")
    logger.info(f"📋 Company ID: {company_id}")
    logger.info(f"🔑 Token: {token[:10]}...")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Тестируем получение сотрудников
            logger.info("👨‍⚕️ Получаем список сотрудников...")
            url = f"{base_url}/staff/{company_id}"
            async with session.get(url, headers=headers) as response:
                staff_data = await response.json()
                logger.info(f"📥 Ответ API ({response.status}): {json.dumps(staff_data, indent=2, ensure_ascii=False)}")
                
                if staff_data.get('success') and staff_data.get('data'):
                    staff = staff_data['data']
                    logger.info(f"Найдено сотрудников: {len(staff)}")
                    for s in staff:
                        logger.info(f"  - {s.get('name', 'Неизвестно')} ({s.get('specialization', 'Неизвестно')})")
                else:
                    logger.error(f" Ошибка получения сотрудников: {staff_data}")
            
            # Тестируем получение услуг
            logger.info("\n🦷 Получаем список услуг...")
            url = f"{base_url}/services/{company_id}"
            async with session.get(url, headers=headers) as response:
                services_data = await response.json()
                logger.info(f"📥 Ответ API ({response.status}): {json.dumps(services_data, indent=2, ensure_ascii=False)}")
                
                if services_data.get('success') and services_data.get('data'):
                    services = services_data['data']
                    logger.info(f"Найдено услуг: {len(services)}")
                    for s in services:
                        logger.info(f"  - {s.get('title', 'Неизвестно')} ({s.get('price_min', 0)}₽)")
                else:
                    logger.warning(f"⚠️ Услуги не найдены или ошибка: {services_data}")
            
        except Exception as e:
            logger.error(f" Ошибка подключения к API: {e}")

if __name__ == "__main__":
    asyncio.run(test_yclients_api())
