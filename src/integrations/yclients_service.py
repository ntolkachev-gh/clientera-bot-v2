#!/usr/bin/env python3
"""
YClients сервис с бизнес-логикой и кешированием.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .yclients_client import create_yclients_client, YClientsAPI
from .cache import Cache
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Кеши с разными TTL
services_cache = Cache(ttl_seconds=3600)  # 1 час для услуг
doctors_cache = Cache(ttl_seconds=86400)  # 24 часа для врачей


class YClientsService:
    """Сервис для работы с YClients API с кешированием и бизнес-логикой."""
    
    def __init__(self):
        """Инициализация сервиса."""
        self.api = create_yclients_client()
        
        # Настройка user token
        user_token = os.getenv("YCLIENTS_USER_TOKEN")
        login = os.getenv("YCLIENTS_LOGIN")
        password = os.getenv("YCLIENTS_PASSWORD")
        
        if user_token:
            self.api.update_user_token(user_token)
            logger.info("YClients user token set from environment variable")
        elif login and password:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Если цикл уже запущен, планируем задачу
                    asyncio.create_task(self._setup_user_token(login, password))
                else:
                    # Если цикл не запущен, выполняем синхронно
                    loop.run_until_complete(self._setup_user_token(login, password))
            except Exception as e:
                logger.warning(f"Failed to get user token: {e}")
        
        logger.info("YClients Service initialized")
        
        # Логируем статус авторизации
        if self.api.user_token:
            logger.info("✅ YClients service initialized with user token")
        else:
            logger.warning("⚠️ YClients service initialized WITHOUT user token - some endpoints may not work")
    
    async def _setup_user_token(self, login: str, password: str):
        """Асинхронная настройка user token."""
        try:
            user_token = await self.api.get_user_token(login, password)
            self.api.update_user_token(user_token)
            logger.info("YClients user token obtained via login/password")
        except Exception as e:
            logger.warning(f"Failed to get user token: {e}")

    async def get_services(self, category: str = "все") -> Dict[str, Any]:
        """Получить список услуг из YClients с кешированием."""
        cache_key = "services_all"  # Кешируем все услуги, фильтрацию делаем после

        try:
            # Проверяем кеш
            cached_services = services_cache.get(cache_key)
            if cached_services:
                logger.info("YCS_GS: Using cached service data (TTL: 1h)")
                # Фильтруем по категории из кеша
                # filtered_services = self._filter_services_by_category(cached_services, category)
                return {"services": cached_services}

            # Кеш пуст или истек, получаем данные из API
            logger.info("YCS_GS: Retrieving fresh service data from YClients API")

            # Получаем все услуги (без привязки к сотруднику)
            services_data = await self.api.get_services()

            if not services_data or not services_data.get('success', False):
                logger.warning(f"API returned error for services: {services_data}")
                raise Exception("Failed to get services data from YClients")

            if not services_data.get('data'):
                raise Exception("No services data in YClients")

            # Преобразуем в наш формат - берем только полезную информацию
            services = []
            for service in services_data['data']:
                service_info = {
                    "name": service.get('title', 'Unknown service'),
                    "price_from": service.get('price_min', 0),
                    "price_to": service.get('price_max', service.get('price_min', 0)),
                    "duration": service.get('duration', 60)
                }

                # Добавляем категорию если есть
                if service.get('category_id'):
                    service_info["category_id"] = service.get('category_id')

                # Добавляем описание если есть
                if service.get('comment') and service.get('comment').strip():
                    service_info["description"] = service.get('comment').strip()

                # Добавляем ID для возможной записи
                if service.get('id'):
                    service_info["id"] = service.get('id')
                    service_info["service_id"] = service.get('id')

                services.append(service_info)

            # Сохраняем в кеш
            services_cache.set(cache_key, services)
            logger.info(f"Saved {len(services)} services to cache (TTL: 1h)")

            # Фильтруем по категории
            # filtered_services = self._filter_services_by_category(services, category)
            return {"services": services}

        except Exception as e:
            logger.error(f"Error retrieving YClients services: {e}")
            raise

    def _filter_services_by_category(self, services: List[Dict], category: str) -> List[Dict]:
        """Фильтрует услуги по категории."""
        if category == "все":
            return services

        filtered = []
        for service in services:
            # Ищем совпадения в названии или описании услуги
            search_fields = [
                service.get("name", ""),
                service.get("description", "")
            ]
            search_text = " ".join(search_fields).lower()

            if category.lower() in search_text:
                filtered.append(service)

        logger.info(f"Filtered {len(filtered)} services by category '{category}'")
        return filtered

    async def get_doctors(self, specialization: str = "все") -> Dict[str, Any]:
        """Получить список врачей из YClients с кешированием."""
        cache_key = "doctors_all"  # Кешируем всех врачей, фильтрацию делаем после

        try:
            # Проверяем кеш
            cached_doctors = doctors_cache.get(cache_key)
            if cached_doctors:
                logger.info("Using cached doctors data (TTL: 24h)")
                # Фильтруем по специализации из кеша
                # filtered_doctors = self._filter_doctors_by_specialization(cached_doctors, specialization)
                return {"doctors": cached_doctors}

            # Кеш пуст или истек, получаем данные из API
            logger.info("Retrieving fresh doctors data from YClients API...")
            staff_data = await self.api.get_staff()
            if not staff_data or not staff_data.get('success', False):
                logger.warning(f"API returned error for staff: {staff_data}")
                raise Exception("Failed to get staff data from YClients")

            if not staff_data.get('data'):
                raise Exception("No staff data in YClients")

            # Преобразуем в наш формат - берем только значимую информацию
            doctors = []
            for staff in staff_data['data']:
                # Получаем основную информацию
                name = staff.get('name', 'Unknown doctor')
                position = staff.get('position', {})
                specialization_text = staff.get('specialization', '')

                # Извлекаем должность и описание
                position_title = position.get('title', 'Specialist') if isinstance(position, dict) else str(position)
                position_description = position.get('description', '') if isinstance(position, dict) else ''

                doctor_info = {
                    "name": name,
                    "position": position_title
                }

                # Добавляем ID врача
                if staff.get('id'):
                    doctor_info["id"] = staff.get('id')

                # Добавляем специализацию из YClients
                if specialization_text and specialization_text.strip():
                    doctor_info["specialization"] = specialization_text.strip()

                # Добавляем описание позиции только если оно есть и не пустое
                if position_description and position_description.strip():
                    doctor_info["description"] = position_description.strip()

                doctors.append(doctor_info)

            # Сохраняем в кеш
            doctors_cache.set(cache_key, doctors)
            logger.info(f"Saved {len(doctors)} doctors to cache (TTL: 24h)")

            return {"doctors": doctors}

        except Exception as e:
            logger.error(f"Error retrieving YClients doctors: {e}")
            raise

    async def search_appointments(self, service: str, doctor: Optional[str] = None, date: Optional[str] = None) -> Dict[str, Any]:
        """Найти свободные слоты через YClients API."""
        try:
            logger.info(f"Searching slots via YClients API: service={service}, doctor={doctor}, date={date}")

            # Определяем дату поиска
            if date:
                search_date = date
            else:
                # Используем завтрашний день по умолчанию
                tomorrow = datetime.now() + timedelta(days=1)
                search_date = tomorrow.strftime('%Y-%m-%d')

            # 1. Найти услугу по названию
            services_result = await self.get_services()
            service_id = None
            for svc in services_result.get('services', []):
                if service.lower() in svc.get('name', '').lower():
                    service_id = svc.get('id')
                    break

            if not service_id:
                logger.warning(f"Service '{service}' not found")
                return {"appointments": []}

            # 2. Найти врача по имени (если указан)
            staff_id = None
            if doctor:
                doctors_result = await self.get_doctors()
                for doc in doctors_result.get('doctors', []):
                    if doctor.lower() in doc.get('name', '').lower():
                        staff_id = doc.get('id')
                        break

                if not staff_id:
                    logger.warning(f"Doctor '{doctor}' not found")
                    return {"appointments": []}

            # 3. Получить всех доступных врачей для услуги, если врач не указан
            if not staff_id:
                staff_data = await self.api.get_staff()
                if staff_data.get('success') and staff_data.get('data'):
                    # Берем первого доступного врача
                    staff_list = staff_data['data']
                    if staff_list:
                        staff_id = staff_list[0].get('id')

            if not staff_id:
                logger.warning("No available doctors found")
                return {"appointments": []}

            # 4. Получить доступные времена
            times_data = await self.api.get_book_times(staff_id, search_date, service_id)
            
            if not times_data.get('success'):
                logger.warning(f"Failed to get available times: {times_data.get('error', 'Unknown error')}")
                return {"appointments": []}

            times = times_data.get('data', [])
            
            # 5. Преобразовать в формат для ответа
            appointments = []
            doctor_name = doctor or "Doctor"
            
            for time_slot in times:
                time_str = time_slot.get('time', '')
                if time_str:
                    appointment = {
                        "datetime": f"{search_date} {time_str}",
                        "doctor": doctor_name,
                        "staff_id": staff_id,
                        "service_id": service_id,
                        "available": True
                    }
                    appointments.append(appointment)

            logger.info(f"Found {len(appointments)} available slots on {search_date}")
            return {"appointments": appointments}

        except Exception as e:
            logger.error(f"Error searching slots: {e}")
            return {"appointments": []}

    async def book_appointment(self, patient_name: str, phone: str, service: str, doctor: str, datetime_str: str, comment: str = "") -> Dict[str, Any]:
        """Записать на прием в YClients с использованием нового формата API."""
        try:
            logger.info(f"Creating appointment: {patient_name}, {service}, {doctor}, {datetime_str}")

            # 1. Найти врача по имени
            doctors_result = await self.get_doctors()
            staff_id = None
            for doc in doctors_result.get('doctors', []):
                if doctor.lower() in doc.get('name', '').lower():
                    staff_id = doc.get('id')
                    break

            if not staff_id:
                raise Exception(f"Doctor '{doctor}' not found")

            # 2. Найти услугу по названию
            services_result = await self.get_services()
            service_id = None
            service_data = None
            for svc in services_result.get('services', []):
                if service.lower() in svc.get('name', '').lower():
                    service_id = svc.get('id')
                    service_data = svc
                    break

            if not service_id:
                raise Exception(f"Service '{service}' not found")
            
            # 2.1. Проверяем, привязана ли услуга к врачу
            if service_data and 'staff' in service_data:
                service_staff_ids = service_data.get('staff', [])
                if service_staff_ids and staff_id not in service_staff_ids:
                    logger.warning(f"Service {service_id} is not assigned to doctor {staff_id}")
                    # Пытаемся привязать услугу к врачу
                    assignment_success = await self._assign_service_to_doctor(service_id, staff_id)
                    
                    if not assignment_success:
                        # Если привязка не удалась, ищем альтернативную услугу
                        logger.info(f"Looking for alternative service for doctor {staff_id}")
                        alternative_service = await self._find_alternative_service(service, staff_id)
                        if alternative_service:
                            service_id = alternative_service['id']
                            logger.info(f"Using alternative service: {alternative_service['name']} (ID: {service_id})")
                        else:
                            logger.warning(f"No alternative service found for doctor {staff_id}")

            # 3. Найти или создать клиента
            client_result = await self.api.find_or_create_client(patient_name, phone)
            if not client_result.get('success'):
                raise Exception(f"Failed to find/create client: {client_result.get('error')}")

            client_data = client_result['data']
            client_id = client_data.get('id')
            if not client_id:
                raise Exception("Failed to get client ID")
            
            # Получаем email клиента или оставляем пустым (как в примере)
            client_email = client_data.get('email') or ""

            # 4. Парсим дату и время
            try:
                dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                date_str = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M")
            except ValueError:
                raise Exception(f"Invalid date/time format: {datetime_str}")

            # 5. Создаем запись - используем правильный формат API
            record_data = {
                "company_id": int(self.api.company_id),
                "name": patient_name,
                "phone": phone,
                "email": client_email,
                "fullname": patient_name,
                "appointments": [{
                    "id": 1,  # Порядковый номер записи
                    "services": [service_id],
                    "staff_id": staff_id,
                    "datetime": f"{date_str}T{time_str}:00+03:00"  # Добавляем часовой пояс
                }],
                "comment": comment or "Запись через бота"
            }

            logger.info(f"📋 Отправляем данные для записи: {record_data}")
            result = await self.api.create_record(record_data)
            
            # Добавляем детальное логирование ответа API
            logger.info(f"🔍 Ответ API create_record: {result}")
            logger.info(f"🔍 Тип result: {type(result)}")
            if isinstance(result, dict) and 'data' in result:
                logger.info(f"🔍 Тип result['data']: {type(result['data'])}")
                logger.info(f"🔍 Содержимое result['data']: {result['data']}")

            if result.get('success'):
                # Безопасная обработка data - может быть список или словарь
                data = result.get('data')
                record_id = None
                
                if isinstance(data, dict):
                    record_id = data.get('id')
                elif isinstance(data, list) and len(data) > 0:
                    # Если data - список, берем первый элемент
                    record_id = data[0].get('id') if isinstance(data[0], dict) else data[0]
                
                logger.info(f"Appointment created successfully: ID {record_id}")
                return {
                    "success": True,
                    "message": f"Appointment successfully created for {datetime_str}",
                    "record_id": record_id,
                    "doctor": doctor,
                    "service": service,
                    "datetime": datetime_str
                }
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"Error creating appointment: {error_msg}")
                return {"success": False, "error": error_msg}

        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            return {"success": False, "error": str(e)}

    async def _assign_service_to_doctor(self, service_id: int, staff_id: int) -> bool:
        """Привязывает услугу к врачу"""
        try:
            logger.info(f"Attempting to assign service {service_id} to doctor {staff_id}")
            
            # Получаем данные услуги
            service_data = await self.api._make_request('GET', f'services/{self.api.company_id}/{service_id}')
            
            if not service_data.get('success'):
                logger.error(f"Failed to get service data: {service_data}")
                return False
            
            service_info = service_data.get('data', {})
            current_staff = service_info.get('staff', [])
            
            if staff_id not in current_staff:
                current_staff.append(staff_id)
                
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
                    f'company/{self.api.company_id}/services/{service_id}',
                    f'services/{self.api.company_id}/{service_id}',
                ]
                
                for endpoint in endpoints:
                    result = await self.api._make_request('PUT', endpoint, update_data)
                    if result.get('success'):
                        logger.info(f"Successfully assigned service {service_id} to doctor {staff_id}")
                        return True
                    else:
                        logger.warning(f"Failed to assign service via {endpoint}: {result}")
                
                logger.error(f"Failed to assign service {service_id} to doctor {staff_id}")
                return False
            else:
                logger.info(f"Service {service_id} is already assigned to doctor {staff_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error assigning service to doctor: {e}")
            return False

    async def _find_alternative_service(self, service_name: str, staff_id: int) -> Optional[Dict]:
        """Ищет альтернативную услугу с похожим названием, привязанную к врачу"""
        try:
            services_result = await self.get_services()
            services = services_result.get('services', [])
            
            # Ищем услуги с похожим названием, привязанные к врачу
            for svc in services:
                svc_name = svc.get('name', '').lower()
                svc_staff = svc.get('staff', [])
                
                # Проверяем, что услуга привязана к врачу и название похоже
                if staff_id in svc_staff and service_name.lower() in svc_name:
                    logger.info(f"Found alternative service: {svc.get('name')} (ID: {svc.get('id')})")
                    return svc
            
            # Если не нашли точное совпадение, ищем по ключевым словам
            service_keywords = service_name.lower().split()
            for svc in services:
                svc_name = svc.get('name', '').lower()
                svc_staff = svc.get('staff', [])
                
                if staff_id in svc_staff:
                    # Проверяем, есть ли общие ключевые слова
                    svc_keywords = svc_name.split()
                    common_keywords = set(service_keywords) & set(svc_keywords)
                    
                    if len(common_keywords) >= 1:  # Хотя бы одно общее слово
                        logger.info(f"Found alternative service by keywords: {svc.get('name')} (ID: {svc.get('id')})")
                        return svc
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding alternative service: {e}")
            return None

    # Методы для управления кешем
    def get_services_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кеша услуг."""
        return services_cache.get_stats()

    def get_doctors_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кеша врачей."""
        return doctors_cache.get_stats()

    def refresh_services_cache(self) -> None:
        """Принудительно обновляет кеш услуг (удаляет текущий кеш)."""
        services_cache.clear()
        logger.info("Services cache cleared")

    def refresh_doctors_cache(self) -> None:
        """Принудительно обновляет кеш врачей (удаляет текущий кеш)."""
        doctors_cache.clear()
        logger.info("Doctors cache cleared")
    
    def clear_all_cache(self) -> None:
        """Очищает все кеши."""
        services_cache.clear()
        doctors_cache.clear()
        logger.info("All caches cleared")
    
    def get_all_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику всех кешей."""
        return {
            "services": self.get_services_cache_stats(),
            "doctors": self.get_doctors_cache_stats()
        }


# Глобальный экземпляр сервиса
_yclients_service: Optional[YClientsService] = None


def get_yclients_service() -> YClientsService:
    """Получить глобальный экземпляр YClients сервиса."""
    global _yclients_service
    
    if _yclients_service is None:
        _yclients_service = YClientsService()
    
    return _yclients_service
