#!/usr/bin/env python3
"""
Скрипт для создания услуг в YClients для конкретных врачей
Создает 30-40 услуг для каждого врача в соответствии с их специализацией.

Врачи (должны уже существовать в системе):
- Магомед Расулов - Врач-эндодонтист (Лечение каналов, ретритмент)
- Мария Соколова - Детская стоматология, герметизация фиссур (Детский стоматолог)
- Тимур Алиев - Удаления, имплантация, синус-лифт (Врач-хирург-имплантолог)
- Елена Петрова - Терапия, профессиональная гигиена (Врач-стоматолог, гигиенист)
- Ирина Волкова - Брекеты, элайнеры, ретейнеры (Врач-ортодонт)
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Any, Optional
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

class DoctorServicesCreator:
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
            raise ValueError("YCLIENTS_TOKEN и YCLIENTS_COMPANY_ID обязательны в .env файле")
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Выполняет HTTP запрос к YClients API"""
        url = f"{self.base_url}/{endpoint}"
        
        headers = self.headers.copy()
        if self.user_token:
            headers['Authorization'] = f'Bearer {self.token}, User {self.user_token}'
        
        logger.debug(f"YClients API {method} {url}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(method, url, headers=headers, json=data) as response:
                    result = await response.json()
                    
                    if response.status >= 400:
                        logger.error(f"YClients API error {response.status}: {result}")
                        return {
                            "success": False,
                            "status_code": response.status,
                            "error": f"HTTP {response.status}: {result.get('message', 'Unknown error')}",
                            "raw_response": result
                        }
                    
                    return result if isinstance(result, dict) else {"success": True, "data": result}
                    
            except Exception as e:
                logger.error(f"YClients API request failed: {e}")
                return {"success": False, "error": str(e)}

    def get_user_token(self, login: str, password: str) -> Optional[str]:
        """Получает user token для расширенных прав"""
        try:
            import requests
        except ImportError:
            logger.error("Модуль requests не установлен. Установите: pip install requests")
            return None
        
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

    async def get_service_categories(self) -> List[Dict]:
        """Получает список категорий услуг"""
        result = await self._make_request('GET', f'service_categories/{self.company_id}')
        if result.get('success') and result.get('data'):
            return result['data']
        return []

    async def create_service(self, service_data: Dict) -> Dict[str, Any]:
        """Создает новую услугу"""
        result = await self._make_request('POST', f'company/{self.company_id}/services', service_data)
        return result

    async def get_current_staff(self) -> List[Dict]:
        """Получает текущий список сотрудников"""
        result = await self._make_request('GET', f'staff/{self.company_id}')
        if result.get('success') and result.get('data'):
            return result['data']
        return []

    def create_service_data(self, title: str, price_min: int, price_max: int, 
                          duration: int, description: str, category_id: int) -> Dict:
        """Создает структуру данных для услуги"""
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

    def get_doctors_data(self) -> Dict[str, Dict]:
        """Возвращает данные врачей с их специализациями"""
        return {
            "Магомед Расулов": {
                "name": "Магомед Расулов",
                "specialization": "врач-эндодонтист",
                "position": "Врач-эндодонтист",
                "phone": "79001234501",
                "email": "magomedrasulov@dental.clinic",
                "information": "Врач-эндодонтист с опытом работы 10 лет. Специализируется на лечении корневых каналов и ретритменте.",
                "services_keywords": ["эндодонт", "канал", "корневой", "пульпит", "периодонтит", "ретритмент", "апексификация"]
            },
            "Мария Соколова": {
                "name": "Мария Соколова", 
                "specialization": "детский стоматолог",
                "position": "Детский стоматолог",
                "phone": "79001234502",
                "email": "mariasokolova@dental.clinic",
                "information": "Детский стоматолог с опытом работы 8 лет. Специализируется на лечении детей и герметизации фиссур.",
                "services_keywords": ["детский", "ребенок", "фиссур", "молочный", "постоянный", "профилактика", "адаптация"]
            },
            "Тимур Алиев": {
                "name": "Тимур Алиев",
                "specialization": "врач-хирург-имплантолог", 
                "position": "Врач-хирург-имплантолог",
                "phone": "79001234503",
                "email": "timuraliev@dental.clinic",
                "information": "Челюстно-лицевой хирург и имплантолог с опытом работы 12 лет. Проводит удаления, имплантацию и синус-лифтинг.",
                "services_keywords": ["удаление", "имплант", "хирург", "синус", "лифт", "костная", "ткань", "остеопластика"]
            },
            "Елена Петрова": {
                "name": "Елена Петрова",
                "specialization": "врач-стоматолог-гигиенист",
                "position": "Врач-стоматолог, гигиенист", 
                "phone": "79001234504",
                "email": "elenapetrov@dental.clinic",
                "information": "Врач-стоматолог и гигиенист с опытом работы 7 лет. Специализируется на терапии и профессиональной гигиене.",
                "services_keywords": ["терапия", "гигиена", "чистка", "кариес", "пломба", "профилактика", "фтор"]
            },
            "Ирина Волкова": {
                "name": "Ирина Волкова",
                "specialization": "врач-ортодонт",
                "position": "Врач-ортодонт",
                "phone": "79001234505", 
                "email": "irinavolkova@dental.clinic",
                "information": "Врач-ортодонт с опытом работы 9 лет. Специализируется на брекетах, элайнерах и ретейнерах.",
                "services_keywords": ["брекет", "элайнер", "ретейнер", "прикус", "ортодонт", "выравнивание", "исправление"]
            }
        }

    def get_services_for_doctors(self, category_id: int) -> Dict[str, List[Dict]]:
        """Генерирует услуги для каждого врача"""
        services_data = {}
        
        # Услуги для Магомеда Расулова - Врач-эндодонтист
        services_data["Магомед Расулов"] = [
            self.create_service_data("Лечение пульпита однокорневого зуба", 8000, 12000, 90, "Эндодонтическое лечение пульпита однокорневого зуба с пломбировкой канала", category_id),
            self.create_service_data("Лечение пульпита двухкорневого зуба", 12000, 16000, 120, "Эндодонтическое лечение пульпита двухкорневого зуба", category_id),
            self.create_service_data("Лечение пульпита трёхкорневого зуба", 15000, 20000, 150, "Эндодонтическое лечение пульпита трёхкорневого зуба", category_id),
            self.create_service_data("Лечение периодонтита однокорневого зуба", 10000, 14000, 120, "Лечение воспаления тканей вокруг корня однокорневого зуба", category_id),
            self.create_service_data("Лечение периодонтита двухкорневого зуба", 14000, 18000, 150, "Лечение периодонтита двухкорневого зуба", category_id),
            self.create_service_data("Лечение периодонтита трёхкорневого зуба", 18000, 25000, 180, "Лечение периодонтита трёхкорневого зуба", category_id),
            self.create_service_data("Ретритмент однокорневого зуба", 12000, 16000, 120, "Повторное эндодонтическое лечение однокорневого зуба", category_id),
            self.create_service_data("Ретритмент двухкорневого зуба", 16000, 22000, 150, "Повторное эндодонтическое лечение двухкорневого зуба", category_id),
            self.create_service_data("Ретритмент трёхкорневого зуба", 22000, 30000, 180, "Повторное эндодонтическое лечение трёхкорневого зуба", category_id),
            self.create_service_data("Распломбировка корневого канала", 3000, 5000, 45, "Удаление старого пломбировочного материала из корневого канала", category_id),
            self.create_service_data("Временная обтурация корневого канала", 2000, 3000, 30, "Временное пломбирование корневого канала лечебной пастой", category_id),
            self.create_service_data("Постоянная обтурация корневого канала", 3000, 4000, 45, "Постоянное пломбирование корневого канала гуттаперчей", category_id),
            self.create_service_data("Апексификация", 8000, 12000, 90, "Лечение зубов с несформированными корнями", category_id),
            self.create_service_data("Внутрикоронковое отбеливание", 5000, 8000, 60, "Отбеливание депульпированного зуба изнутри", category_id),
            self.create_service_data("Закрытие перфорации корня", 6000, 10000, 90, "Устранение перфорации корня зуба биосовместимыми материалами", category_id),
            self.create_service_data("Резекция верхушки корня", 8000, 12000, 90, "Хирургическое удаление верхушки корня зуба", category_id),
            self.create_service_data("Эндодонтическая консультация", 2000, 2000, 30, "Консультация врача-эндодонтиста с составлением плана лечения", category_id),
            self.create_service_data("Контрольный рентген после эндолечения", 800, 800, 15, "Рентгенологический контроль качества пломбирования каналов", category_id),
            self.create_service_data("Медикаментозная обработка корневых каналов", 2000, 3000, 30, "Антисептическая обработка корневых каналов", category_id),
            self.create_service_data("Механическая обработка корневых каналов", 3000, 5000, 45, "Инструментальная обработка корневых каналов", category_id),
            self.create_service_data("Ультразвуковая активация в эндодонтии", 2000, 3000, 30, "Ультразвуковая активация ирригационных растворов", category_id),
            self.create_service_data("Восстановление зуба после эндолечения", 5000, 8000, 60, "Реставрация коронковой части зуба после эндодонтического лечения", category_id),
            self.create_service_data("Извлечение инородного тела из канала", 4000, 8000, 60, "Удаление сломанного инструмента или штифта из корневого канала", category_id),
            self.create_service_data("Создание апикального упора", 2000, 3000, 30, "Формирование апикального сужения в корневом канале", category_id),
            self.create_service_data("Лечение зуба с кальцификацией каналов", 10000, 15000, 120, "Эндодонтическое лечение зуба с облитерированными каналами", category_id),
            self.create_service_data("Витальная ампутация пульпы", 4000, 6000, 45, "Частичное удаление пульпы с сохранением жизнеспособности корневой части", category_id),
            self.create_service_data("Витальная экстирпация пульпы", 6000, 8000, 60, "Полное удаление живой пульпы зуба", category_id),
            self.create_service_data("Девитальная экстирпация пульпы", 5000, 7000, 60, "Удаление некротизированной пульпы зуба", category_id),
            self.create_service_data("Лечение зуба с широким апикальным отверстием", 8000, 12000, 90, "Эндодонтическое лечение зуба с незакрытой верхушкой корня", category_id),
            self.create_service_data("Эндодонтическое лечение под микроскопом", 15000, 25000, 150, "Лечение корневых каналов с использованием операционного микроскопа", category_id),
            self.create_service_data("Трепанация коронки зуба", 2000, 3000, 30, "Создание доступа к корневым каналам через коронку зуба", category_id),
            self.create_service_data("Наложение девитализирующей пасты", 1500, 2000, 20, "Наложение пасты для некротизации пульпы", category_id),
            self.create_service_data("Снятие девитализирующей пасты", 1000, 1500, 15, "Удаление девитализирующей пасты из полости зуба", category_id),
            self.create_service_data("Повторное эндодонтическое лечение с микроскопом", 20000, 35000, 180, "Ретритмент с использованием операционного микроскопа", category_id),
            self.create_service_data("Обтурация каналов термопластифицированной гуттаперчей", 5000, 8000, 60, "Пломбирование каналов разогретой гуттаперчей", category_id),
            self.create_service_data("Лечение травматического пульпита", 8000, 12000, 90, "Эндодонтическое лечение пульпита после травмы зуба", category_id),
            self.create_service_data("Эндодонтическое лечение при периостите", 10000, 15000, 120, "Лечение корневых каналов при гнойном воспалении надкостницы", category_id),
            self.create_service_data("Лечение зуба с внутренней резорбцией", 12000, 18000, 150, "Эндодонтическое лечение зуба с внутренним рассасыванием тканей", category_id),
            self.create_service_data("Эндодонтическое лечение с использованием лазера", 12000, 20000, 120, "Лазерная стерилизация корневых каналов", category_id),
            self.create_service_data("Консультация по сложному эндодонтическому случаю", 3000, 3000, 45, "Расширенная консультация по сложным случаям эндодонтии", category_id)
        ]
        
        # Услуги для Марии Соколовой - Детский стоматолог
        services_data["Мария Соколова"] = [
            self.create_service_data("Детская стоматологическая консультация", 1500, 1500, 30, "Первичная консультация детского стоматолога", category_id),
            self.create_service_data("Лечение кариеса молочного зуба", 2500, 4000, 45, "Лечение кариеса временного зуба у ребенка", category_id),
            self.create_service_data("Лечение кариеса постоянного зуба у ребенка", 3000, 5000, 60, "Лечение кариеса постоянного зуба у ребенка", category_id),
            self.create_service_data("Герметизация фиссур", 2000, 2000, 30, "Запечатывание естественных углублений в зубах", category_id),
            self.create_service_data("Удаление молочного зуба", 1500, 2500, 20, "Удаление временного зуба у ребенка", category_id),
            self.create_service_data("Лечение пульпита молочного зуба", 4000, 6000, 60, "Эндодонтическое лечение молочного зуба", category_id),
            self.create_service_data("Профессиональная гигиена детям", 2500, 3500, 45, "Профессиональная чистка зубов для детей", category_id),
            self.create_service_data("Фторирование зубов детям", 1500, 1500, 20, "Укрепление детской эмали фторсодержащими препаратами", category_id),
            self.create_service_data("Серебрение молочных зубов", 1000, 1500, 15, "Обработка кариозных зубов раствором серебра", category_id),
            self.create_service_data("Установка детской коронки", 5000, 8000, 60, "Установка готовой коронки на молочный зуб", category_id),
            self.create_service_data("Лечение под седацией", 8000, 12000, 90, "Стоматологическое лечение ребенка под седацией", category_id),
            self.create_service_data("Адаптационный визит", 1000, 1000, 30, "Знакомство ребенка с кабинетом и врачом", category_id),
            self.create_service_data("Урок гигиены для детей", 1500, 1500, 30, "Обучение ребенка правильной чистке зубов", category_id),
            self.create_service_data("Лечение стоматита у детей", 2000, 3000, 30, "Лечение воспаления слизистой оболочки рта", category_id),
            self.create_service_data("Пластика уздечки языка у детей", 5000, 8000, 45, "Хирургическая коррекция короткой уздечки языка", category_id),
            self.create_service_data("Пластика уздечки губы у детей", 4000, 6000, 45, "Хирургическая коррекция уздечки губы", category_id),
            self.create_service_data("Лечение гингивита у детей", 2500, 4000, 45, "Лечение воспаления десен у ребенка", category_id),
            self.create_service_data("Восстановление зуба стеклоиономером", 2000, 3500, 45, "Реставрация детского зуба стеклоиономерным цементом", category_id),
            self.create_service_data("Лечение травмы зуба у ребенка", 3000, 6000, 60, "Лечение поврежденного в результате травмы зуба", category_id),
            self.create_service_data("Реплантация зуба", 8000, 15000, 120, "Приживление выбитого зуба обратно в лунку", category_id),
            self.create_service_data("Шинирование подвижных зубов у детей", 5000, 8000, 60, "Фиксация подвижных зубов после травмы", category_id),
            self.create_service_data("Лечение периодонтита молочного зуба", 4000, 7000, 75, "Лечение воспаления тканей вокруг корня молочного зуба", category_id),
            self.create_service_data("Цветная пломба для детей", 3000, 4000, 45, "Установка цветной пломбы для мотивации ребенка", category_id),
            self.create_service_data("Лечение под наркозом", 15000, 25000, 120, "Стоматологическое лечение ребенка под общим наркозом", category_id),
            self.create_service_data("Профилактика кариеса у детей", 2000, 2000, 30, "Комплекс профилактических мероприятий", category_id),
            self.create_service_data("Лечение меловидных пятен", 2500, 4000, 45, "Лечение начального кариеса в стадии пятна", category_id),
            self.create_service_data("Удаление зубного налета у детей", 2000, 3000, 30, "Снятие мягких зубных отложений", category_id),
            self.create_service_data("Покрытие зубов защитным лаком", 1500, 2000, 20, "Нанесение фторсодержащего лака на зубы", category_id),
            self.create_service_data("Лечение бутылочного кариеса", 5000, 10000, 90, "Лечение множественного кариеса у детей раннего возраста", category_id),
            self.create_service_data("Восстановление формы зуба у ребенка", 3500, 5000, 60, "Реставрация анатомической формы детского зуба", category_id),
            self.create_service_data("Лечение кисты молочного зуба", 6000, 10000, 90, "Лечение кистозного образования у корня молочного зуба", category_id),
            self.create_service_data("Консультация для родителей", 1000, 1000, 20, "Консультация родителей по уходу за зубами ребенка", category_id),
            self.create_service_data("Снятие зубного камня у подростков", 3000, 4000, 45, "Профессиональное удаление твердых зубных отложений", category_id),
            self.create_service_data("Лечение зубов в игровой форме", 4000, 6000, 60, "Лечение с использованием игровых методик", category_id),
            self.create_service_data("Полировка пломб у детей", 1000, 1500, 20, "Шлифовка и полировка установленных пломб", category_id),
            self.create_service_data("Детское отбеливание зубов", 5000, 8000, 45, "Безопасное осветление зубов у подростков", category_id),
            self.create_service_data("Лечение аномалий развития зубов", 6000, 12000, 90, "Коррекция врожденных аномалий зубов", category_id),
            self.create_service_data("Диспансерное наблюдение", 1500, 1500, 30, "Регулярное наблюдение за состоянием зубов ребенка", category_id),
            self.create_service_data("Рентген зубов детям", 800, 800, 15, "Рентгенологическое исследование зубов у детей", category_id),
            self.create_service_data("Ортодонтическая консультация детям", 2000, 2000, 30, "Консультация по исправлению прикуса у детей", category_id)
        ]
        
        # Услуги для Тимура Алиева - Врач-хирург-имплантолог
        services_data["Тимур Алиев"] = [
            self.create_service_data("Консультация хирурга-имплантолога", 2500, 2500, 45, "Консультация челюстно-лицевого хирурга и имплантолога", category_id),
            self.create_service_data("Удаление зуба простое", 2000, 3000, 30, "Удаление подвижного или разрушенного зуба", category_id),
            self.create_service_data("Удаление зуба сложное", 5000, 8000, 60, "Сложное удаление зуба с разрезом десны", category_id),
            self.create_service_data("Удаление зуба мудрости", 8000, 15000, 90, "Удаление ретинированного или дистопированного зуба мудрости", category_id),
            self.create_service_data("Установка импланта", 35000, 50000, 90, "Хирургическая установка зубного импланта", category_id),
            self.create_service_data("Синус-лифтинг открытый", 30000, 45000, 120, "Открытая операция по увеличению объема костной ткани верхней челюсти", category_id),
            self.create_service_data("Синус-лифтинг закрытый", 20000, 30000, 60, "Закрытая операция синус-лифтинга одновременно с имплантацией", category_id),
            self.create_service_data("Костная пластика", 25000, 40000, 120, "Увеличение объема костной ткани для имплантации", category_id),
            self.create_service_data("Удаление ретинированного зуба", 12000, 20000, 120, "Удаление непрорезавшегося зуба", category_id),
            self.create_service_data("Резекция верхушки корня", 8000, 12000, 90, "Хирургическое удаление верхушки корня зуба", category_id),
            self.create_service_data("Цистэктомия", 10000, 18000, 120, "Удаление кисты челюстно-лицевой области", category_id),
            self.create_service_data("Гемисекция корня", 8000, 12000, 90, "Удаление одного из корней многокорневого зуба", category_id),
            self.create_service_data("Вскрытие абсцесса", 3000, 5000, 30, "Хирургическое лечение гнойного воспаления", category_id),
            self.create_service_data("Лечение альвеолита", 2000, 3000, 30, "Лечение воспаления лунки после удаления зуба", category_id),
            self.create_service_data("Кюретаж лунки", 2000, 3000, 30, "Выскабливание лунки после удаления зуба", category_id),
            self.create_service_data("Остановка кровотечения", 2000, 4000, 30, "Гемостаз после хирургического вмешательства", category_id),
            self.create_service_data("Наложение швов", 1500, 2500, 20, "Ушивание операционной раны", category_id),
            self.create_service_data("Снятие швов", 1000, 1500, 15, "Удаление хирургических швов", category_id),
            self.create_service_data("Формирователь десны", 5000, 8000, 30, "Установка формирователя десны на имплант", category_id),
            self.create_service_data("Направленная костная регенерация", 20000, 35000, 120, "НКР с использованием мембран и костных материалов", category_id),
            self.create_service_data("Пластика десны", 8000, 15000, 60, "Коррекция контура и объема десны", category_id),
            self.create_service_data("Удаление экзостоза", 5000, 10000, 45, "Удаление костного выроста", category_id),
            self.create_service_data("Альвеолопластика", 8000, 15000, 90, "Коррекция альвеолярного отростка", category_id),
            self.create_service_data("Удаление импланта", 8000, 15000, 60, "Хирургическое удаление несостоявшегося импланта", category_id),
            self.create_service_data("Лоскутная операция", 12000, 20000, 120, "Хирургическое лечение пародонтита", category_id),
            self.create_service_data("Удаление новообразования", 8000, 20000, 90, "Хирургическое удаление доброкачественного новообразования", category_id),
            self.create_service_data("Биопсия", 5000, 8000, 30, "Забор ткани для гистологического исследования", category_id),
            self.create_service_data("Реимплантация зуба", 10000, 18000, 120, "Возвращение зуба в лунку после полного вывиха", category_id),
            self.create_service_data("Коронарно-радикулярная сепарация", 8000, 12000, 90, "Разделение коронки и корня зуба", category_id),
            self.create_service_data("Удаление инородного тела", 5000, 12000, 60, "Извлечение инородного тела из мягких тканей", category_id),
            self.create_service_data("Пластика перфорации пазухи", 8000, 15000, 90, "Закрытие перфорации верхнечелюстной пазухи", category_id),
            self.create_service_data("Установка мини-импланта", 15000, 25000, 45, "Установка ортодонтического мини-импланта", category_id),
            self.create_service_data("Скуловая имплантация", 80000, 120000, 180, "Установка скулового импланта при атрофии кости", category_id),
            self.create_service_data("All-on-4 имплантация", 200000, 350000, 240, "Полная имплантация челюсти на 4 имплантах", category_id),
            self.create_service_data("All-on-6 имплантация", 250000, 400000, 300, "Полная имплантация челюсти на 6 имплантах", category_id),
            self.create_service_data("Немедленная имплантация", 40000, 60000, 120, "Установка импланта сразу после удаления зуба", category_id),
            self.create_service_data("Отсроченная имплантация", 35000, 50000, 90, "Установка импланта через 3-6 месяцев после удаления", category_id),
            self.create_service_data("Контрольный осмотр после имплантации", 1500, 1500, 30, "Послеоперационный контроль приживления импланта", category_id),
            self.create_service_data("Снятие слепков с имплантов", 3000, 5000, 45, "Получение оттисков для изготовления коронки на имплант", category_id),
            self.create_service_data("Хирургический шаблон для имплантации", 15000, 25000, 60, "Изготовление и использование хирургического шаблона", category_id)
        ]
        
        # Услуги для Елены Петровой - Врач-стоматолог, гигиенист
        services_data["Елена Петрова"] = [
            self.create_service_data("Консультация стоматолога-гигиениста", 1500, 1500, 30, "Консультация по гигиене полости рта и профилактике", category_id),
            self.create_service_data("Профессиональная гигиена полости рта", 4000, 6000, 60, "Комплексная профессиональная чистка зубов", category_id),
            self.create_service_data("Ультразвуковая чистка зубов", 3000, 4000, 45, "Удаление зубного камня ультразвуком", category_id),
            self.create_service_data("Air Flow чистка", 3500, 3500, 30, "Чистка зубов методом Air Flow", category_id),
            self.create_service_data("Лечение кариеса", 3000, 6000, 60, "Лечение кариеса с установкой пломбы", category_id),
            self.create_service_data("Художественная реставрация зуба", 8000, 15000, 90, "Эстетическая реставрация зуба композитными материалами", category_id),
            self.create_service_data("Установка световой пломбы", 2500, 5000, 45, "Установка светоотверждаемой пломбы", category_id),
            self.create_service_data("Полировка зубов", 2000, 2000, 30, "Полировка зубов специальными пастами", category_id),
            self.create_service_data("Фторирование зубов", 1500, 2000, 20, "Укрепление эмали фторсодержащими препаратами", category_id),
            self.create_service_data("Глубокое фторирование", 2500, 3000, 30, "Интенсивное фторирование эмали", category_id),
            self.create_service_data("Реминерализация эмали", 2000, 3000, 30, "Восстановление минерального состава эмали", category_id),
            self.create_service_data("Лечение повышенной чувствительности", 2500, 4000, 45, "Десенситивная терапия при гиперестезии", category_id),
            self.create_service_data("Лечение начального кариеса", 2000, 3500, 30, "Лечение кариеса в стадии пятна", category_id),
            self.create_service_data("Снятие мягкого налета", 2000, 2500, 30, "Удаление бактериального налета", category_id),
            self.create_service_data("Снятие пигментированного налета", 2500, 3500, 45, "Удаление налета от кофе, чая, табака", category_id),
            self.create_service_data("Обучение гигиене полости рта", 1500, 1500, 30, "Индивидуальное обучение правильной чистке зубов", category_id),
            self.create_service_data("Подбор средств гигиены", 1000, 1000, 20, "Рекомендации по выбору зубной щетки и пасты", category_id),
            self.create_service_data("Контролируемая чистка зубов", 2000, 2000, 30, "Обучение технике чистки под контролем врача", category_id),
            self.create_service_data("Лечение клиновидного дефекта", 3000, 5000, 45, "Восстановление клиновидного дефекта пломбой", category_id),
            self.create_service_data("Лечение эрозии эмали", 4000, 8000, 60, "Лечение эрозивных поражений эмали", category_id),
            self.create_service_data("Покрытие зубов защитным лаком", 2000, 2500, 20, "Нанесение фторсодержащего лака", category_id),
            self.create_service_data("Аппликации лечебных препаратов", 1500, 2500, 20, "Нанесение лекарственных средств на зубы", category_id),
            self.create_service_data("Лечение поверхностного кариеса", 2500, 4000, 45, "Лечение кариеса в пределах эмали", category_id),
            self.create_service_data("Лечение среднего кариеса", 3500, 6000, 60, "Лечение кариеса с поражением дентина", category_id),
            self.create_service_data("Лечение глубокого кариеса", 4500, 8000, 75, "Лечение кариеса близко к пульпе", category_id),
            self.create_service_data("Лечебная прокладка под пломбу", 1500, 2000, 15, "Наложение лечебной прокладки", category_id),
            self.create_service_data("Изолирующая прокладка", 1000, 1500, 10, "Наложение изолирующей прокладки", category_id),
            self.create_service_data("Временная пломба", 1500, 2000, 20, "Установка временной пломбы", category_id),
            self.create_service_data("Замена старой пломбы", 3000, 5000, 45, "Замена несостоятельной пломбы", category_id),
            self.create_service_data("Шлифовка и полировка пломбы", 1500, 2000, 20, "Коррекция формы и полировка пломбы", category_id),
            self.create_service_data("Профилактический осмотр", 1000, 1000, 20, "Регулярный осмотр состояния зубов", category_id),
            self.create_service_data("Составление плана лечения", 1500, 1500, 30, "Разработка индивидуального плана лечения", category_id),
            self.create_service_data("Лечение множественного кариеса", 8000, 15000, 120, "Комплексное лечение множественных кариозных поражений", category_id),
            self.create_service_data("Восстановление контактного пункта", 2000, 3000, 30, "Восстановление межзубного контакта", category_id),
            self.create_service_data("Коррекция формы зуба", 3000, 6000, 60, "Восстановление анатомической формы зуба", category_id),
            self.create_service_data("Устранение диастемы", 8000, 15000, 90, "Закрытие промежутка между передними зубами", category_id),
            self.create_service_data("Лечение некариозных поражений", 3000, 6000, 60, "Лечение флюороза, гипоплазии эмали", category_id),
            self.create_service_data("Профилактика кариеса", 2000, 3000, 30, "Комплекс профилактических мероприятий", category_id),
            self.create_service_data("Индивидуальная профилактическая программа", 2500, 2500, 45, "Разработка персональной программы профилактики", category_id),
            self.create_service_data("Контроль качества гигиены", 1500, 1500, 20, "Оценка эффективности домашней гигиены", category_id)
        ]
        
        # Услуги для Ирины Волковой - Врач-ортодонт
        services_data["Ирина Волкова"] = [
            self.create_service_data("Ортодонтическая консультация", 2000, 2000, 45, "Консультация врача-ортодонта с планом лечения", category_id),
            self.create_service_data("Установка металлических брекетов", 80000, 100000, 120, "Установка металлической брекет-системы", category_id),
            self.create_service_data("Установка керамических брекетов", 100000, 120000, 120, "Установка эстетических керамических брекетов", category_id),
            self.create_service_data("Установка сапфировых брекетов", 120000, 150000, 120, "Установка прозрачных сапфировых брекетов", category_id),
            self.create_service_data("Установка лингвальных брекетов", 200000, 300000, 150, "Установка невидимых брекетов с внутренней стороны", category_id),
            self.create_service_data("Лечение элайнерами", 150000, 250000, 90, "Исправление прикуса прозрачными капами", category_id),
            self.create_service_data("Активация брекет-системы", 3000, 5000, 45, "Плановая коррекция брекет-системы", category_id),
            self.create_service_data("Снятие брекет-системы", 15000, 20000, 120, "Снятие брекетов и полировка зубов", category_id),
            self.create_service_data("Установка ретейнеров", 15000, 25000, 60, "Установка несъемных ретейнеров", category_id),
            self.create_service_data("Изготовление съемного ретейнера", 12000, 18000, 45, "Изготовление съемной ретенционной каппы", category_id),
            self.create_service_data("Коррекция ретейнера", 3000, 5000, 30, "Подгонка и коррекция ретейнера", category_id),
            self.create_service_data("Замена дуги в брекетах", 2000, 4000, 30, "Замена ортодонтической дуги", category_id),
            self.create_service_data("Установка дополнительных элементов", 2000, 5000, 30, "Установка пружин, эластиков, кнопок", category_id),
            self.create_service_data("Лечение детей съемными аппаратами", 25000, 40000, 60, "Ортодонтическое лечение съемными пластинками", category_id),
            self.create_service_data("Миофункциональная терапия", 8000, 15000, 45, "Коррекция функций мышц челюстно-лицевой области", category_id),
            self.create_service_data("Сепарация зубов", 2000, 3000, 30, "Создание места между зубами", category_id),
            self.create_service_data("Фиксация брекета", 1500, 2500, 20, "Приклеивание отклеившегося брекета", category_id),
            self.create_service_data("Замена брекета", 2000, 3000, 30, "Замена сломанного или потерянного брекета", category_id),
            self.create_service_data("Установка микроимпланта", 15000, 25000, 45, "Установка ортодонтического микроимпланта", category_id),
            self.create_service_data("Расширение верхней челюсти", 30000, 50000, 90, "Расширение суженной верхней челюсти аппаратом", category_id),
            self.create_service_data("Дистализация моляров", 20000, 35000, 60, "Перемещение жевательных зубов назад", category_id),
            self.create_service_data("Интрузия зубов", 15000, 25000, 60, "Вертикальное перемещение зубов в кость", category_id),
            self.create_service_data("Экструзия зубов", 12000, 20000, 60, "Вытягивание зуба из кости", category_id),
            self.create_service_data("Ортодонтическая подготовка к протезированию", 40000, 80000, 120, "Выравнивание зубов перед протезированием", category_id),
            self.create_service_data("Лечение дисфункции ВНЧС", 25000, 45000, 90, "Ортодонтическое лечение нарушений ВНЧС", category_id),
            self.create_service_data("Изготовление каппы от бруксизма", 8000, 12000, 45, "Защитная каппа при скрежете зубами", category_id),
            self.create_service_data("Спортивная защитная каппа", 6000, 10000, 30, "Индивидуальная каппа для занятий спортом", category_id),
            self.create_service_data("Трейнер для детей", 8000, 15000, 30, "Миофункциональный трейнер для коррекции прикуса", category_id),
            self.create_service_data("Коррекция скученности зубов", 80000, 150000, 120, "Лечение скученного положения зубов", category_id),
            self.create_service_data("Закрытие диастемы ортодонтически", 60000, 100000, 90, "Закрытие промежутка между зубами брекетами", category_id),
            self.create_service_data("Исправление глубокого прикуса", 100000, 180000, 150, "Ортодонтическое лечение глубокого прикуса", category_id),
            self.create_service_data("Исправление открытого прикуса", 120000, 200000, 180, "Лечение открытого прикуса", category_id),
            self.create_service_data("Исправление перекрестного прикуса", 100000, 160000, 150, "Коррекция перекрестного смыкания", category_id),
            self.create_service_data("Лечение мезиального прикуса", 150000, 250000, 200, "Исправление нижней прогнатии", category_id),
            self.create_service_data("Лечение дистального прикуса", 120000, 200000, 180, "Исправление верхней прогнатии", category_id),
            self.create_service_data("Ортодонтическая диагностика", 5000, 8000, 60, "Комплексная диагностика с анализом моделей", category_id),
            self.create_service_data("Снятие слепков для брекетов", 2000, 3000, 30, "Получение оттисков для изготовления аппаратов", category_id),
            self.create_service_data("Контрольный осмотр в процессе лечения", 2000, 2000, 30, "Плановый контроль хода ортодонтического лечения", category_id),
            self.create_service_data("Профессиональная гигиена при брекетах", 4000, 6000, 60, "Специальная чистка зубов с брекет-системой", category_id),
            self.create_service_data("Обучение гигиене при брекетах", 1500, 1500, 30, "Инструктаж по уходу за брекет-системой", category_id)
        ]
        
        return services_data

    async def get_existing_doctors(self) -> Dict[str, int]:
        """Получает существующих врачей и возвращает их ID"""
        doctors_data = self.get_doctors_data()
        existing_doctors = {}
        
        # Получаем существующих сотрудников
        existing_staff = await self.get_current_staff()
        existing_names = [staff.get('name', '') for staff in existing_staff]
        
        for doctor_name in doctors_data.keys():
            # Проверяем, есть ли уже такой врач
            if doctor_name in existing_names:
                logger.info(f"👨‍⚕️ Врач {doctor_name} найден")
                # Находим ID существующего врача
                for staff in existing_staff:
                    if staff.get('name') == doctor_name:
                        existing_doctors[doctor_name] = staff.get('id')
                        break
            else:
                logger.warning(f"⚠️ Врач {doctor_name} не найден в системе")
        
        return existing_doctors

    async def create_services_for_doctors(self, doctor_ids: Dict[str, int]) -> Dict[str, List[int]]:
        """Создает услуги для врачей"""
        # Получаем категории услуг
        categories = await self.get_service_categories()
        if not categories:
            logger.error("❌ Нет категорий услуг! Создайте хотя бы одну категорию.")
            return {}
        
        category_id = categories[0]['id']
        logger.info(f"📋 Используем категорию: {categories[0]['title']} (ID: {category_id})")
        
        # Получаем услуги для врачей
        services_data = self.get_services_for_doctors(category_id)
        created_services = {}
        
        for doctor_name, doctor_services in services_data.items():
            if doctor_name not in doctor_ids:
                logger.warning(f"⚠️ Врач {doctor_name} не найден в системе")
                continue
            
            doctor_id = doctor_ids[doctor_name]
            logger.info(f"🦷 Создаем услуги для {doctor_name} ({len(doctor_services)} услуг)")
            created_services[doctor_name] = []
            
            for service_data in doctor_services:
                logger.info(f"  ➕ Создаем: {service_data['title']}")
                
                # Добавляем врача к услуге при создании
                service_data['staff'] = [doctor_id]
                
                result = await self.create_service(service_data)
                if result.get('success'):
                    service_id = result.get('data', {}).get('id')
                    if service_id:
                        created_services[doctor_name].append(service_id)
                        logger.info(f"    ✅ Услуга создана и привязана к врачу (ID: {service_id})")
                    else:
                        logger.error(f"    ❌ Не удалось получить ID услуги")
                else:
                    logger.error(f"    ❌ Ошибка создания услуги: {result}")
        
        return created_services

    async def assign_services_to_doctors(self, doctor_ids: Dict[str, int], services_ids: Dict[str, List[int]]):
        """Привязывает услуги к врачам"""
        logger.info("🔗 Привязываем услуги к врачам...")
        
        for doctor_name, service_ids in services_ids.items():
            if doctor_name not in doctor_ids:
                continue
            
            doctor_id = doctor_ids[doctor_name]
            logger.info(f"👨‍⚕️ Привязываем {len(service_ids)} услуг к {doctor_name}")
            
            # Получаем данные услуги для обновления
            for service_id in service_ids:
                # Сначала получаем данные услуги
                service_data = await self._make_request('GET', f'services/{self.company_id}/{service_id}')
                
                if not service_data.get('success'):
                    logger.warning(f"  ⚠️ Не удалось получить данные услуги {service_id}")
                    continue
                
                # Обновляем данные услуги, добавляя врача
                service_info = service_data.get('data', {})
                current_staff = service_info.get('staff', [])
                
                if doctor_id not in current_staff:
                    current_staff.append(doctor_id)
                
                # Подготавливаем данные для обновления
                update_data = {
                    "title": service_info.get('title'),
                    "booking_title": service_info.get('booking_title'),
                    "category_id": service_info.get('category_id'),
                    "price_min": service_info.get('price_min'),
                    "price_max": service_info.get('price_max'),
                    "duration": service_info.get('duration'),
                    "comment": service_info.get('comment'),
                    "active": service_info.get('active'),
                    "is_multi": service_info.get('is_multi'),
                    "tax_variant": service_info.get('tax_variant'),
                    "vat_id": service_info.get('vat_id'),
                    "is_need_limit_date": service_info.get('is_need_limit_date'),
                    "seance_search_start": service_info.get('seance_search_start'),
                    "seance_search_step": service_info.get('seance_search_step'),
                    "step": service_info.get('step'),
                    "seance_search_finish": service_info.get('seance_search_finish'),
                    "staff": current_staff
                }
                
                # Пробуем разные endpoints для обновления
                endpoints = [
                    f'company/{self.company_id}/services/{service_id}',
                    f'services/{self.company_id}/{service_id}',
                ]
                
                success = False
                for endpoint in endpoints:
                    result = await self._make_request('PUT', endpoint, update_data)
                    if result.get('success'):
                        success = True
                        break
                
                if success:
                    logger.info(f"  ✅ Услуга {service_id} привязана к {doctor_name}")
                else:
                    logger.warning(f"  ⚠️ Не удалось привязать услугу {service_id} к врачу {doctor_name}")

    async def show_summary(self, doctor_ids: Dict[str, int], services_ids: Dict[str, List[int]]):
        """Показывает итоговую статистику"""
        logger.info("\n" + "="*60)
        logger.info("📊 ИТОГОВАЯ СТАТИСТИКА")
        logger.info("="*60)
        
        total_doctors = len(doctor_ids)
        total_services = sum(len(services) for services in services_ids.values())
        
        logger.info(f"👨‍⚕️ Создано врачей: {total_doctors}")
        logger.info(f"🦷 Создано услуг: {total_services}")
        
        for doctor_name, doctor_id in doctor_ids.items():
            services_count = len(services_ids.get(doctor_name, []))
            logger.info(f"  • {doctor_name} (ID: {doctor_id}): {services_count} услуг")
        
        logger.info("="*60)

    async def fill_all_data(self):
        """Основная функция заполнения данных"""
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
            
            logger.info("🚀 Начинаем создание услуг для врачей...")
            
            # 1. Получаем существующих врачей
            doctor_ids = await self.get_existing_doctors()
            if not doctor_ids:
                logger.error("❌ Не найдено ни одного врача в системе")
                return
            
            # 2. Создаем услуги для врачей (с автоматической привязкой)
            services_ids = await self.create_services_for_doctors(doctor_ids)
            if not services_ids:
                logger.error("❌ Не удалось создать ни одной услуги")
                return
            
            # 3. Показываем итоговую статистику
            await self.show_summary(doctor_ids, services_ids)
            
            logger.info("🎉 Заполнение данных завершено!")
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            raise

async def main():
    """Главная функция"""
    try:
        creator = DoctorServicesCreator()
        await creator.fill_all_data()
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
