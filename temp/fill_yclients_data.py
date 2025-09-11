#!/usr/bin/env python3
"""
Скрипт для заполнения YClients тестовыми данными (услуги и врачи)
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

class YClientsDataFiller:
    def __init__(self):
        self.token = os.getenv("YCLIENTS_TOKEN")
        self.company_id = os.getenv("YCLIENTS_COMPANY_ID")
        self.user_token = None
        self.base_url = "https://api.yclients.com/api/v1"
        self.headers = {
            'Accept': 'application/vnd.yclients.v2+json',
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        if not all([self.token, self.company_id]):
            raise ValueError("Clients настройки обязательны! Проверьте YCLIENTS_TOKEN и YCLIENTS_COMPANY_ID в .env файл")
    
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
                        logger.info(f"📥 YClients API ответ ({response.status})")
                        return result
                elif method == 'POST':
                    async with session.post(url, headers=headers, json=data) as response:
                        result = await response.json()
                        logger.info(f"📥 YClients API ответ ({response.status})")
                        return result
                elif method == 'PUT':
                    async with session.put(url, headers=headers, json=data) as response:
                        result = await response.json()
                        logger.info(f"📥 YClients API ответ ({response.status})")
                        return result
            except Exception as e:
                logger.error(f"Ошибка запроса к YClients API: {e}")
                return {"success": False, "error": str(e)}
    
    def get_user_token(self, login, password):
        """Получает user token для расширенных прав"""
        import requests
        
        url = f"{self.base_url}/auth"
        data = {
            "login": login,
            "password": password
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            result = response.json()
            if result.get('success') and result.get('data', {}).get('user_token'):
                return result['data']['user_token']
            else:
                logger.warning(f"Не удалось получить user token: {result}")
                return None
        except Exception as e:
            logger.error(f"Ошибка получения user token: {e}")
            return None
    
    async def get_current_staff(self):
        """Получает текущий список сотрудников"""
        result = await self._make_request('GET', f'staff/{self.company_id}')
        if result.get('success') and result.get('data'):
            return result['data']
        return []
    
    async def get_current_services(self):
        """Получает текущий список услуг"""
        result = await self._make_request('GET', f'services/{self.company_id}')
        if result.get('success') and result.get('data'):
            return result['data']
        return []
    
    async def get_service_categories(self):
        """Получает список категорий услуг"""
        result = await self._make_request('GET', f'service_categories/{self.company_id}')
        if result.get('success') and result.get('data'):
            return result['data']
        return []
    
    async def create_service(self, service_data):
        """Создает новую услугу"""
        result = await self._make_request('POST', f'company/{self.company_id}/services', service_data)
        return result
    
    async def create_staff(self, staff_data):
        """Создает нового сотрудника"""
        result = await self._make_request('POST', f'staff/{self.company_id}', staff_data)
        return result
    
    async def fill_services(self):
        """Заполняет услуги тестовыми данными"""
        logger.info("🦷 Заполняем услуги...")
        
        # Получаем категории услуг
        categories = await self.get_service_categories()
        if not categories:
            logger.error("Нет категорий услуг! Создайте хотя бы одну категорию.")
            return []
        
        category_id = categories[0]['id']  # Берем первую доступную категорию
        logger.info(f"📋 Используем категорию: {categories[0]['title']} (ID: {category_id})")
        
        # Функция для создания правильной структуры услуги
        def create_service_data(title, price_min, price_max, duration, description):
            return {
                "title": title,
                "booking_title": title,
                "category_id": category_id,
                "price_min": price_min,
                "price_max": price_max,
                "duration": duration,
                "comment": description,
                "active": 1,
                "is_multi": False,
                "tax_variant": 1,
                "vat_id": 1,
                "is_need_limit_date": False,
                "seance_search_start": 0,
                "seance_search_step": 15,
                "step": 15,
                "seance_search_finish": 1440,
                "staff": []
            }
        
        # Расширенный список услуг для стоматологической клиники
        test_services = [
            # Консультации и диагностика
            create_service_data("Консультация стоматолога", 1500, 1500, 30, "Первичная консультация стоматолога с осмотром полости рта"),
            create_service_data("Консультация ортодонта", 2000, 2000, 45, "Консультация по исправлению прикуса и выравниванию зубов"),
            create_service_data("Консультация хирурга", 2500, 2500, 30, "Консультация челюстно-лицевого хирурга"),
            create_service_data("Рентгенография зуба", 800, 800, 15, "Прицельный рентгеновский снимок зуба"),
            create_service_data("Панорамный снимок", 2500, 2500, 20, "Ортопантомограмма - панорамный снимок челюстей"),
            
            # Терапевтическое лечение
            create_service_data("Лечение кариеса", 3000, 5000, 60, "Лечение кариеса с установкой пломбы"),
            create_service_data("Лечение пульпита", 8000, 12000, 90, "Эндодонтическое лечение корневых каналов"),
            create_service_data("Лечение периодонтита", 10000, 15000, 120, "Лечение воспаления тканей вокруг корня зуба"),
            create_service_data("Художественная реставрация", 8000, 15000, 90, "Эстетическая реставрация зуба композитными материалами"),
            create_service_data("Установка пломбы", 2500, 6000, 45, "Установка световой пломбы различных типов"),
            
            # Профилактика и гигиена
            create_service_data("Профессиональная чистка зубов", 4000, 4000, 45, "Ультразвуковая чистка зубов и полировка"),
            create_service_data("Air Flow чистка", 3500, 3500, 30, "Чистка зубов методом Air Flow"),
            create_service_data("Фторирование зубов", 1500, 1500, 20, "Укрепление эмали фторсодержащими препаратами"),
            create_service_data("Герметизация фиссур", 2000, 2000, 30, "Запечатывание естественных углублений в зубах"),
            
            # Хирургия
            create_service_data("Удаление зуба простое", 2000, 3000, 30, "Удаление подвижного или разрушенного зуба"),
            create_service_data("Удаление зуба сложное", 5000, 8000, 60, "Сложное удаление зуба с разрезом десны"),
            create_service_data("Удаление зуба мудрости", 8000, 12000, 90, "Удаление ретинированного зуба мудрости"),
            create_service_data("Имплантация зуба", 35000, 50000, 120, "Установка зубного импланта с коронкой"),
            create_service_data("Синус-лифтинг", 25000, 35000, 90, "Операция по увеличению объема костной ткани"),
            
            # Протезирование
            create_service_data("Коронка металлокерамическая", 12000, 15000, 60, "Установка металлокерамической коронки"),
            create_service_data("Коронка керамическая", 18000, 25000, 60, "Установка цельнокерамической коронки"),
            create_service_data("Коронка циркониевая", 25000, 35000, 60, "Установка коронки из диоксида циркония"),
            create_service_data("Съемный протез частичный", 20000, 30000, 120, "Изготовление частичного съемного протеза"),
            create_service_data("Съемный протез полный", 35000, 50000, 150, "Изготовление полного съемного протеза"),
            
            # Ортодонтия
            create_service_data("Установка брекетов металлических", 80000, 100000, 90, "Установка металлических брекетов"),
            create_service_data("Установка брекетов керамических", 100000, 120000, 90, "Установка керамических брекетов"),
            create_service_data("Установка брекетов сапфировых", 120000, 150000, 90, "Установка сапфировых брекетов"),
            create_service_data("Исправление прикуса элайнерами", 150000, 200000, 60, "Лечение капами-элайнерами"),
            
            # Эстетическая стоматология
            create_service_data("Отбеливание зубов ZOOM", 15000, 20000, 60, "Профессиональное отбеливание системой ZOOM"),
            create_service_data("Отбеливание зубов домашнее", 8000, 12000, 30, "Изготовление кап для домашнего отбеливания"),
            create_service_data("Установка виниров", 25000, 40000, 90, "Установка керамических виниров"),
            create_service_data("Установка люминиров", 35000, 50000, 90, "Установка ультратонких люминиров")
        ]
        
        created_services = []
        for service in test_services:
            logger.info(f"➕ Создаем услугу: {service['title']}")
            result = await self.create_service(service)
            if result.get('success'):
                logger.info(f"Услуга создана: {service['title']}")
                created_services.append(result['data'])
            else:
                logger.error(f" Ошибка создания услуги {service['title']}: {result}")
        
        return created_services
    
    async def fill_staff(self):
        """Заполняет врачей тестовыми данными"""
        logger.info("👨‍⚕️ Заполняем врачей...")
        
        # Тестовые врачи для стоматологической клиники
        test_staff = [
            {
                "name": "Иванова Анна Петровна",
                "specialization": "стоматолог-терапевт",
                "phone": "79001234567",
                "email": "ivanova@dental.clinic",
                "position_id": 0,
                "bookable": True,
                "information": "Стоматолог-терапевт с опытом работы 8 лет. Специализируется на лечении кариеса и эндодонтии.",
                "rating": 4.8
            },
            {
                "name": "Петров Михаил Александрович", 
                "specialization": "стоматолог-хирург",
                "phone": "79001234568",
                "email": "petrov@dental.clinic",
                "position_id": 0,
                "bookable": True,
                "information": "Челюстно-лицевой хирург с опытом 12 лет. Проводит имплантацию и сложные удаления.",
                "rating": 4.9
            },
            {
                "name": "Сидорова Елена Владимировна",
                "specialization": "стоматолог-гигиенист",
                "phone": "79001234569", 
                "email": "sidorova@dental.clinic",
                "position_id": 0,
                "bookable": True,
                "information": "Специалист по профессиональной гигиене полости рта и профилактике.",
                "rating": 4.7
            },
            {
                "name": "Козлов Дмитрий Сергеевич",
                "specialization": "стоматолог-ортопед",
                "phone": "79001234570",
                "email": "kozlov@dental.clinic", 
                "position_id": 0,
                "bookable": True,
                "information": "Врач-ортопед, специализируется на протезировании и реставрации зубов.",
                "rating": 4.6
            },
            {
                "name": "Николаева Ольга Игоревна",
                "specialization": "стоматолог-пародонтолог",
                "phone": "79001234571",
                "email": "nikolaeva@dental.clinic",
                "position_id": 0, 
                "bookable": True,
                "information": "Специалист по лечению заболеваний десен и пародонта.",
                "rating": 4.5
            }
        ]
        
        created_staff = []
        for staff in test_staff:
            logger.info(f"➕ Создаем врача: {staff['name']}")
            result = await self.create_staff(staff)
            if result.get('success'):
                logger.info(f"Врач создан: {staff['name']}")
                created_staff.append(result['data'])
            else:
                logger.error(f" Ошибка создания врача {staff['name']}: {result}")
        
        return created_staff
    
    async def show_current_data(self):
        """Показывает текущие данные в YClients"""
        logger.info("📋 Текущие данные в YClients:")
        
        # Показываем сотрудников
        staff = await self.get_current_staff()
        logger.info(f"👨‍⚕️ Сотрудников: {len(staff)}")
        for s in staff:
            logger.info(f"  - {s.get('name', 'Неизвестно')} ({s.get('specialization', 'Неизвестно')})")
        
        # Показываем услуги
        services = await self.get_current_services()
        logger.info(f"🦷 Услуг: {len(services)}")
        for s in services:
            logger.info(f"  - {s.get('title', 'Неизвестно')} ({s.get('price_min', 0)}₽)")
    
    async def fill_all_data(self):
        """Заполняет все тестовые данные"""
        try:
            # Получаем user token если есть логин/пароль
            login = os.getenv("YCLIENTS_LOGIN")
            password = os.getenv("YCLIENTS_PASSWORD")
            
            if login and password:
                self.user_token = self.get_user_token(login, password)
                if self.user_token:
                    logger.info("✅ User token получен")
                else:
                    logger.warning("⚠️ Работаем без user token (ограниченные права)")
            
            logger.info("🚀 Начинаем заполнение данных YClients...")
            
            # Показываем текущие данные
            await self.show_current_data()
            
            # Заполняем услуги
            services = await self.fill_services()
            logger.info(f"Создано услуг: {len(services)}")
            
            # Заполняем врачей
            staff = await self.fill_staff()
            logger.info(f"Создано врачей: {len(staff)}")
            
            # Показываем обновленные данные
            logger.info("\n" + "="*50)
            await self.show_current_data()
            
            logger.info("🎉 Заполнение данных завершено!")
            
        except Exception as e:
            logger.error(f" Ошибка заполнения данных: {e}")
            raise

async def main():
    """Главная функция"""
    try:
        filler = YClientsDataFiller()
        await filler.fill_all_data()
    except Exception as e:
        logger.error(f" Критическая ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
