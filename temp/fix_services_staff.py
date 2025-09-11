#!/usr/bin/env python3
"""
Скрипт для привязки услуг к врачам в YClients
"""

import asyncio
import json
import logging
import os
from dotenv import load_dotenv
import aiohttp
import requests

# Загружаем .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class YClientsServiceStaffFixer:
    def __init__(self):
        self.token = os.getenv('YCLIENTS_TOKEN')
        self.company_id = os.getenv('YCLIENTS_COMPANY_ID')
        self.form_id = os.getenv('YCLIENTS_FORM_ID')
        self.user_token = None
        self.base_url = "https://api.yclients.com/api/v1"
        self.headers = {
            'Accept': 'application/vnd.yclients.v2+json',
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        # Получаем user token
        try:
            login = os.getenv('YCLIENTS_LOGIN')
            password = os.getenv('YCLIENTS_PASSWORD')
            if login and password:
                user_token = self.get_user_token(login, password)
                if user_token:
                    self.user_token = user_token
                    logger.info("✅ User token получен")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить user token: {e}")
    
    def get_user_token(self, login, password):
        """Получает user token через синхронный запрос"""
        url = f"{self.base_url}/user/auth"
        data = {
            "login": login,
            "password": password
        }
        headers = {
            'Accept': 'application/vnd.yclients.v2+json',
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            result = response.json()
            if result.get('success') and result.get('data', {}).get('user_token'):
                return result['data']['user_token']
            return None
        except Exception as e:
            logger.error(f"Ошибка получения user token: {e}")
            return None
    
    async def _make_request(self, method, endpoint, data=None):
        """Выполняет HTTP запрос к YClients API"""
        url = f"{self.base_url}/{endpoint}"
        headers = self.headers.copy()
        if self.user_token:
            headers['Authorization'] = f'Bearer {self.token}, User {self.user_token}'
        
        logger.info(f"🔗 YClients API запрос: {method} {url}")
        
        async with aiohttp.ClientSession() as session:
            try:
                if method == 'GET':
                    async with session.get(url, headers=headers) as response:
                        result = await response.json()
                        logger.info(f"📥 YClients API ответ ({response.status}): статус={result.get('success')}")
                        return result
                elif method == 'PUT':
                    async with session.put(url, headers=headers, json=data) as response:
                        result = await response.json()
                        logger.info(f"📥 YClients API ответ ({response.status}): статус={result.get('success')}")
                        return result
            except Exception as e:
                logger.error(f"Ошибка запроса к YClients API: {e}")
                return {"success": False, "error": str(e)}
    
    async def get_all_staff(self):
        """Получает всех сотрудников"""
        result = await self._make_request('GET', f'staff/{self.company_id}')
        if result.get('success'):
            return result.get('data', [])
        return []
    
    async def get_all_services(self):
        """Получает все услуги"""
        result = await self._make_request('GET', f'services/{self.company_id}')
        if result.get('success'):
            return result.get('data', [])
        return []
    
    async def update_service_staff(self, service_id, staff_ids):
        """Обновляет привязку услуги к сотрудникам"""
        # Пробуем разные endpoints
        endpoints_to_try = [
            f'company/{self.company_id}/services/{service_id}',
            f'services/{self.company_id}/{service_id}',
            f'service/{service_id}',
            f'company/{self.company_id}/service/{service_id}'
        ]
        
        data = {
            "staff": staff_ids
        }
        
        for endpoint in endpoints_to_try:
            logger.info(f"   🔄 Пробуем endpoint: {endpoint}")
            result = await self._make_request('PUT', endpoint, data)
            if result.get('success'):
                logger.info(f"   ✅ Успешно через endpoint: {endpoint}")
                return True
            else:
                logger.info(f"    Ошибка через endpoint: {endpoint} - {result.get('meta', {}).get('message', 'неизвестная ошибка')}")
        
        return False
    
    async def fix_services_staff_mapping(self):
        """Привязывает услуги к подходящим врачам"""
        logger.info("🚀 Начинаем привязку услуг к врачам...")
        
        # Получаем всех врачей
        staff = await self.get_all_staff()
        logger.info(f"👨‍⚕️ Найдено врачей: {len(staff)}")
        
        # Получаем все услуги
        services = await self.get_all_services()
        logger.info(f"🦷 Найдено услуг: {len(services)}")
        
        # Создаем маппинг специализаций к услугам
        specialization_services = {
            "стоматолог-терапевт": [
                "Консультация стоматолога", "Лечение кариеса", "Лечение пульпита", 
                "Лечение периодонтита", "Художественная реставрация", "Установка пломбы"
            ],
            "стоматолог-хирург": [
                "Консультация хирурга", "Удаление зуба простое", "Удаление зуба сложное", 
                "Удаление зуба мудрости", "Имплантация зуба", "Синус-лифтинг", "Удаление зуба"
            ],
            "стоматолог-ортопед": [
                "Коронка металлокерамическая", "Коронка керамическая", "Коронка циркониевая",
                "Съемный протез частичный", "Съемный протез полный"
            ],
            "стоматолог-гигиенист": [
                "Профессиональная чистка зубов", "Air Flow чистка", "Фторирование зубов",
                "Герметизация фиссур"
            ],
            "ортодонт": [
                "Консультация ортодонта", "Установка брекетов металлических", 
                "Установка брекетов керамических", "Установка брекетов сапфировых",
                "Исправление прикуса элайнерами", "Установка брекетов"
            ],
            "стоматолог-пародонтолог": [
                "Лечение периодонтита", "Профессиональная чистка зубов"
            ]
        }
        
        # Общие услуги для всех врачей
        universal_services = [
            "Рентгенография зуба", "Панорамный снимок", "Отбеливание зубов ZOOM",
            "Отбеливание зубов домашнее", "Установка виниров", "Установка люминиров",
            "Отбеливание зубов"
        ]
        
        updated_services = 0
        
        # Обрабатываем каждую услугу
        for service in services:
            service_title = service.get('title', '')
            service_id = service.get('id')
            
            if not service_title or service_title == "Услуга":
                continue
                
            logger.info(f"🔧 Обрабатываем услугу: {service_title}")
            
            # Найдем подходящих врачей
            suitable_staff = []
            
            # Если это универсальная услуга - добавляем всех врачей
            if service_title in universal_services:
                suitable_staff = [s['id'] for s in staff]
                logger.info(f"   📋 Универсальная услуга - назначаем всем {len(suitable_staff)} врачам")
            else:
                # Найдем врачей по специализации
                for staff_member in staff:
                    specialization = staff_member.get('specialization', '')
                    if specialization in specialization_services:
                        if service_title in specialization_services[specialization]:
                            suitable_staff.append(staff_member['id'])
                
                logger.info(f"   👨‍⚕️ Найдено подходящих врачей: {len(suitable_staff)}")
            
            # Обновляем услугу
            if suitable_staff:
                success = await self.update_service_staff(service_id, suitable_staff)
                if success:
                    updated_services += 1
                    logger.info(f"   ✅ Услуга обновлена")
                else:
                    logger.warning(f"   ⚠️ Не удалось обновить услугу")
            else:
                logger.warning(f"    Не найдено подходящих врачей")
        
        logger.info(f"🎉 Обновлено услуг: {updated_services} из {len(services)}")
        return updated_services

async def main():
    fixer = YClientsServiceStaffFixer()
    await fixer.fix_services_staff_mapping()

if __name__ == "__main__":
    asyncio.run(main())
