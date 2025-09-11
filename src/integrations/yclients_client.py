#!/usr/bin/env python3
"""
YClients API низкоуровневый HTTP клиент.
"""

import os
import aiohttp
from typing import Dict, Any, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


class YClientsAPI:
    """Низкоуровневый HTTP клиент для YClients API."""
    
    def __init__(self, token: str, company_id: str, form_id: str = "0"):
        self.token = token
        self.company_id = company_id
        self.form_id = form_id
        self.user_token: Optional[str] = None
        self.base_url = "https://api.yclients.com/api/v1"
        self.headers = {
            'Accept': 'application/vnd.yclients.v2+json',
            'Content-Type': 'application/json'
        }

    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Выполняет HTTP запрос к YClients API"""
        url = f"{self.base_url}/{endpoint}"

        headers = self.headers.copy()
        if self.user_token:
            # Формат: Bearer token, User user_token
            headers['Authorization'] = f'Bearer {self.token}, User {self.user_token}'
        else:
            # Для запросов без user token используем только основной токен
            headers['Authorization'] = f'Bearer {self.token}'

        logger.debug(f"YClients API {method} {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, json=data) as response:
                    response_data = await response.json()
                    
                    if response.status >= 400:
                        logger.error(f"YClients API error {response.status}: {response_data}")
                        return {
                            "success": False,
                            "status_code": response.status,
                            "error": f"HTTP {response.status}: {response_data.get('message', 'Unknown error')}",
                            "raw_response": response_data
                        }
                    
                    # Нормализуем ответ - если это не словарь, оборачиваем
                    if isinstance(response_data, dict):
                        return response_data
                    else:
                        # Если ответ не словарь (например, список), оборачиваем его
                        return {
                            "success": True,
                            "data": response_data
                        }
                    
        except Exception as e:
            logger.error(f"YClients API request failed: {e}")
            return {"success": False, "error": str(e)}

    def update_user_token(self, user_token: str) -> None:
        """Обновляет user token для авторизованных запросов."""
        self.user_token = user_token
        logger.info("✅ YClients user token обновлен")

    async def get_user_token(self, login: str, password: str) -> str:
        """Получает user token через логин/пароль"""
        data = {
            "login": login,
            "password": password
        }
        
        response = await self._make_request('POST', 'auth', data)
        
        if not response.get('success'):
            raise Exception(f"Не удалось получить user token: {response.get('error', 'Unknown error')}")
        
        user_token = response.get('data', {}).get('user_token')
        if not user_token:
            raise Exception("User token не найден в ответе API")
        
        return user_token

    async def get_services(self, staff_id: Optional[int] = None) -> Dict[str, Any]:
        """Получает список услуг"""
        endpoint = f'services/{self.company_id}'
        if staff_id:
            endpoint += f'?staff_id={staff_id}'
        return await self._make_request('GET', endpoint)

    async def get_staff(self) -> Dict[str, Any]:
        """Получает список сотрудников"""
        endpoint = f'book_staff/{self.company_id}'
        return await self._make_request('GET', endpoint)

    async def get_book_dates(self, staff_id: int, service_id: int) -> Dict[str, Any]:
        """Получает доступные даты для записи"""
        endpoint = f'book_dates/{self.company_id}/{staff_id}/{service_id}'
        return await self._make_request('GET', endpoint)

    async def get_book_times(self, staff_id: int, service_id: int, date: str) -> Dict[str, Any]:
        """Получает доступные времена для записи на конкретную дату"""
        endpoint = f'book_times/{self.company_id}/{staff_id}/{date}'
        return await self._make_request('GET', endpoint)

    async def create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает запись на прием"""
        endpoint = f'book_record/{self.company_id}'
        return await self._make_request('POST', endpoint, data)

    async def get_records(self, staff_id: Optional[int] = None, date: Optional[str] = None) -> Dict[str, Any]:
        """Получает список записей"""
        endpoint = f'records/{self.company_id}'
        params = []
        
        if staff_id:
            params.append(f'staff_id={staff_id}')
        if date:
            params.append(f'date={date}')
            
        if params:
            endpoint += '?' + '&'.join(params)
            
        return await self._make_request('GET', endpoint)

    async def get_company_info(self) -> Dict[str, Any]:
        """Получает информацию о компании"""
        endpoint = f'company/{self.company_id}'
        return await self._make_request('GET', endpoint)

    async def create_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает нового клиента"""
        endpoint = f'clients/{self.company_id}'
        return await self._make_request('POST', endpoint, client_data)

    async def find_or_create_client(self, name: str, phone: str) -> Dict[str, Any]:
        """Находит существующего клиента или создает нового"""
        
        # Функция для нормализации телефона
        def normalize_phone(phone_str: str) -> str:
            return phone_str.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        
        # Сначала пытаемся найти клиента по телефону
        search_endpoint = f'clients/{self.company_id}?phone={phone}'
        search_result = await self._make_request('GET', search_endpoint)
        
        if search_result.get('success') and search_result.get('data'):
            # Клиент найден
            clients = search_result['data']
            if clients:
                client = clients[0]  # Берем первого найденного клиента
                logger.info(f"📱 Найден существующий клиент: {client.get('name', name)}")
                return {"success": True, "data": client}
        
        # Клиент не найден, создаем нового
        logger.info(f"➕ Создаем нового клиента: {name}")
        client_data = {
            "name": name,
            "phone": phone,
            "sex_id": 0  # Не указано
        }
        
        create_result = await self.create_client(client_data)
        
        # Если получили ошибку 422 (клиент уже существует), пытаемся найти его еще раз
        if not create_result.get('success') and create_result.get('status_code') == 422:
            logger.warning(f"⚠️ Клиент с телефоном {phone} уже существует, повторный поиск...")
            
            # Пробуем различные варианты поиска
            search_variants = [
                phone,  # Оригинальный номер
                phone.replace('+7', '8'),  # +7 -> 8
                phone.replace('8', '+7', 1) if phone.startswith('8') else phone,  # 8 -> +7
                normalize_phone(phone),  # Только цифры
            ]
            
            # Убираем дубликаты
            search_variants = list(set(search_variants))
            
            for variant in search_variants:
                if variant == phone:
                    continue  # Уже пробовали выше
                    
                logger.debug(f"🔍 Пробуем поиск с вариантом телефона: {variant}")
                search_endpoint = f'clients/{self.company_id}?phone={variant}'
                variant_result = await self._make_request('GET', search_endpoint)
                
                if variant_result.get('success') and variant_result.get('data'):
                    clients = variant_result['data']
                    if clients:
                        client = clients[0]
                        logger.info(f"📱 Найден существующий клиент через вариант {variant}: {client.get('name', name)}")
                        return {"success": True, "data": client}
            
            # Если все варианты не сработали, делаем поиск по всем клиентам
            logger.debug("🔍 Поиск среди всех клиентов...")
            all_clients_endpoint = f'clients/{self.company_id}'
            all_clients_result = await self._make_request('GET', all_clients_endpoint)
            
            if all_clients_result.get('success') and all_clients_result.get('data'):
                clients = all_clients_result['data']
                clean_phone = normalize_phone(phone)
                
                for client in clients:
                    client_phone = client.get('phone', '')
                    clean_client_phone = normalize_phone(client_phone)
                    
                    if clean_client_phone == clean_phone:
                        logger.info(f"📱 Найден существующий клиент через полный поиск: {client.get('name', name)} (тел: {client_phone})")
                        return {"success": True, "data": client}
            
            # Если все еще не нашли, возвращаем ошибку создания
            logger.error(f"❌ Не удалось найти клиента с телефоном {phone}, хотя система говорит что он существует")
            logger.error(f"❌ Детали ошибки: {create_result.get('raw_response', {})}")
            return create_result
        
        return create_result


def create_yclients_client() -> YClientsAPI:
    """Создает экземпляр YClients API клиента с настройками из переменных окружения."""
    token = os.getenv("YCLIENTS_TOKEN")
    company_id = os.getenv("YCLIENTS_COMPANY_ID")
    form_id = os.getenv("YCLIENTS_FORM_ID", "0")
    
    if not token or not company_id:
        raise ValueError("YCLIENTS_TOKEN и YCLIENTS_COMPANY_ID обязательны в .env файле")
    
    return YClientsAPI(token=token, company_id=company_id, form_id=form_id)
