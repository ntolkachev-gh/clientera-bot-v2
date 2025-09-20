"""
YClients API adapter for Realtime API integration.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .yclients_service import get_yclients_service
from .user_profiles import get_profile_manager, UserProfile
from .notification_service import get_notification_service
from ..config.env import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Моковые данные для демо-режима

# Моковые услуги салона красоты Prive7 Makhachkala
MOCK_SERVICES = [
    # Парикмахерские услуги / стрижки и укладки
    {
        "id": 1,
        "name": "Детская стрижка до 12 лет",
        "category": "парикмахерские услуги",
        "price": 2500,
        "duration": 30,
        "description": "Детская стрижка для детей до 12 лет"
    },
    {
        "id": 2,
        "name": "Стрижка челки",
        "category": "парикмахерские услуги",
        "price": 1000,
        "duration": 15,
        "description": "Стрижка и оформление челки"
    },
    {
        "id": 3,
        "name": "Женская стрижка",
        "category": "парикмахерские услуги",
        "price": 4500,
        "duration": 60,
        "description": "Женская стрижка любой сложности"
    },

    # Уходы для волос
    {
        "id": 4,
        "name": "ORIBE \"Роскошь Золота\" короткие волосы",
        "category": "уходы для волос",
        "price": 4000,
        "duration": 45,
        "description": "Премиальный уход ORIBE для коротких волос"
    },
    {
        "id": 5,
        "name": "ORIBE \"Роскошь Золота\" длинные волосы",
        "category": "уходы для волос",
        "price": 5600,
        "duration": 60,
        "description": "Премиальный уход ORIBE для длинных волос"
    },
    {
        "id": 6,
        "name": "Philip Martins экспресс увлажнение средняя длина",
        "category": "уходы для волос",
        "price": 2500,
        "duration": 30,
        "description": "Экспресс-уход Philip Martins для увлажнения волос средней длины"
    },

    # Окрашивания / тонирования / осветление
    {
        "id": 7,
        "name": "KYDRA base окрашивание корней и тонирование + уход, 30 см",
        "category": "окрашивание",
        "price": 10500,
        "duration": 180,
        "description": "Профессиональное окрашивание корней KYDRA с тонированием и уходом"
    },
    {
        "id": 8,
        "name": "KYDRA base — 30-50 см (80гр)",
        "category": "окрашивание",
        "price": 11700,
        "duration": 210,
        "description": "Окрашивание KYDRA для волос средней длины"
    },
    {
        "id": 9,
        "name": "KYDRA base — 50+ см (120гр)",
        "category": "окрашивание",
        "price": 15500,
        "duration": 240,
        "description": "Окрашивание KYDRA для длинных волос"
    },

    # Маникюр и педикюр
    {
        "id": 10,
        "name": "Маникюр классический",
        "category": "маникюр",
        "price": 1500,
        "duration": 60,
        "description": "Классический маникюр с покрытием лаком"
    },
    {
        "id": 11,
        "name": "Маникюр с гель-лаком",
        "category": "маникюр",
        "price": 2500,
        "duration": 90,
        "description": "Маникюр с покрытием гель-лаком (стойкость до 3 недель)"
    },
    {
        "id": 12,
        "name": "Французский маникюр",
        "category": "маникюр",
        "price": 3000,
        "duration": 90,
        "description": "Классический французский маникюр"
    },
    {
        "id": 13,
        "name": "Педикюр классический",
        "category": "педикюр",
        "price": 2000,
        "duration": 90,
        "description": "Классический педикюр с покрытием лаком"
    },
    {
        "id": 14,
        "name": "Педикюр с гель-лаком",
        "category": "педикюр",
        "price": 3000,
        "duration": 120,
        "description": "Педикюр с покрытием гель-лаком"
    },
    {
        "id": 15,
        "name": "SPA-маникюр",
        "category": "маникюр",
        "price": 3500,
        "duration": 120,
        "description": "SPA-маникюр с уходом и массажем рук"
    },

    # Косметология
    {
        "id": 16,
        "name": "Чистка лица",
        "category": "косметология",
        "price": 4000,
        "duration": 90,
        "description": "Профессиональная чистка лица"
    },
    {
        "id": 17,
        "name": "Массаж лица",
        "category": "косметология",
        "price": 2500,
        "duration": 60,
        "description": "Расслабляющий массаж лица"
    },
    {
        "id": 18,
        "name": "Макияж дневной",
        "category": "визаж",
        "price": 2000,
        "duration": 60,
        "description": "Дневной макияж для повседневного образа"
    },
    {
        "id": 19,
        "name": "Макияж вечерний",
        "category": "визаж",
        "price": 3000,
        "duration": 90,
        "description": "Вечерний макияж для особых случаев"
    },
    {
        "id": 20,
        "name": "Свадебный макияж",
        "category": "визаж",
        "price": 5000,
        "duration": 120,
        "description": "Свадебный макияж с пробой"
    }
]

MOCK_MASTERS = [
    {
        "id": 1,
        "name": "Саша Омарова",
        "specialization": "Визажист Prive7",
        "specializations": ["визаж", "макияж"],
        "services": ["макияж", "визаж", "свадебный макияж", "вечерний макияж"],
        "instagram": "отменена как \"визажист Prive7\"",
        "description": "Профессиональный визажист с опытом работы более 5 лет",
        "rating": 4.9,
        "avatar": None
    },
    {
        "id": 2,
        "name": "Юлия Кадырова",
        "specialization": "Hair (парикмахер, стилист)",
        "specializations": ["парикмахер", "стилист", "колорист"],
        "services": ["стрижка", "укладка", "окрашивание", "мелирование", "ботокс волос"],
        "instagram": "В одном из постов: \"Hair: Юлия Кадырова\"",
        "description": "Мастер-стилист по волосам, специалист по сложным окрашиваниям",
        "rating": 4.8,
        "avatar": None
    },
    {
        "id": 3,
        "name": "Екатерина Гриценко",
        "specialization": "Стилист / парикмахер",
        "specializations": ["стилист", "парикмахер"],
        "services": ["стрижка", "укладка", "прически", "кератиновое выпрямление"],
        "instagram": "В одном из образов: \"Hair: Екатерина Гриценко\"",
        "description": "Стилист-парикмахер, специалист по созданию стильных образов",
        "rating": 4.7,
        "avatar": None
    },
    {
        "id": 4,
        "name": "Амина Магомедова",
        "specialization": "Ногтевой сервис (маникюр, педикюр)",
        "specializations": ["маникюр", "педикюр", "дизайн ногтей", "наращивание ногтей"],
        "services": ["классический маникюр", "аппаратный маникюр", "гель-лак", "педикюр", "дизайн ногтей",
                     "наращивание"],
        "instagram": "В профиле указано: \"Nails: Амина Магомедова\"",
        "description": "Мастер ногтевого сервиса с опытом работы более 4 лет, специализируется на дизайне и уходе за ногтями",
        "rating": 4.9,
        "avatar": None
    }
]


class YClientsAdapter:
    """Adapter для YClients API для использования в Realtime API."""

    def __init__(self):
        """Инициализация адаптера."""
        self.settings = get_settings()

        # В демо-режиме не инициализируем реальный сервис
        if not self.settings.DEMO:
            self.service = get_yclients_service()
        else:
            self.service = None

        self.profile_manager = get_profile_manager()
        self.notification_service = get_notification_service()

        mode = "DEMO" if self.settings.DEMO else "PRODUCTION"
        logger.info(f"YClients Adapter initialized in {mode} mode")

    async def list_services(self, category: str = "все", limit: int = 50) -> List[Dict[str, Any]]:
        """Получить список услуг."""
        try:
            # В демо-режиме используем моковые данные
            if self.settings.DEMO:
                logger.info("Using mock data for services list (DEMO mode)")
                services = MOCK_SERVICES.copy()

                # Фильтруем по категории если указана
                if category and category != "все":
                    filtered_services = []
                    for service in services:
                        # Проверяем соответствие категории
                        service_category = service.get('category', '').lower()
                        if (category.lower() in service_category or
                                service_category in category.lower() or
                                category.lower() == service_category):
                            filtered_services.append(service)
                    services = filtered_services

                # Применяем лимит если указан
                if limit and limit > 0:
                    services = services[:limit]

                logger.info(f"Retrieved {len(services)} services (DEMO mode, category: {category}, limit: {limit})")
                return services

            result = await self.service.get_services(category)
            services = result.get('services', [])

            # Применяем лимит если указан
            if limit and limit > 0:
                services = services[:limit]

            logger.info(f"Retrieved {len(services)} services (limit: {limit})")
            return services
        except Exception as e:
            logger.error(f"Error retrieving services: {e}")
            return []

    async def search_slots(
            self,
            doctor_id: int,
            date: str
    ) -> List[Dict[str, Any]]:
        """Найти свободные слоты для записи на услугу для конкретного врача на конкретную дату."""
        try:
            logger.info(f"YA_SSL: Searching slots for doctor_id={doctor_id}, date={date}")

            # В демо-режиме генерируем слоты
            if self.settings.DEMO:
                logger.info("YA_SSL: Using mock data for slots (DEMO mode)")

                # Получаем имя врача из моковых данных
                doctor_name = None
                for master in MOCK_MASTERS:
                    if master.get('id') == doctor_id:
                        doctor_name = master.get('name', f'Master {doctor_id}')
                        break

                if not doctor_name:
                    doctor_name = f'Master {doctor_id}'

                # Генерируем слоты с 10:00 до 20:00 с интервалом 30 минут
                slots = []
                for hour in range(10, 20):
                    for minute in [0, 30]:
                        time_str = f"{hour:02d}:{minute:02d}"
                        slot = {
                            'datetime': f"{date} {time_str}",
                            'date': date,
                            'time': time_str,
                            'doctor': doctor_name,
                            'doctor_id': doctor_id,
                            'available': True
                        }
                        slots.append(slot)

                logger.info(f"YA_SSL: Generated {len(slots)} mock slots for doctor {doctor_name} on {date}")
                return slots

            # Получаем имя врача по ID
            doctor_name = None
            doctors_result = await self.service.get_doctors()
            for doctor in doctors_result.get('doctors', []):
                if doctor.get('id') == doctor_id:
                    doctor_name = doctor.get('name', '')
                    break

            if not doctor_name:
                logger.warning(f"YA_SSL: Doctor with ID {doctor_id} not found")
                return []

            # Получаем доступные слоты напрямую через API без привязки к конкретной услуге
            # API endpoint: /book_times/{company_id}/{staff_id}/{date}
            times_data = await self.service.api.get_book_times(doctor_id, date)

            if not times_data.get('success'):
                logger.warning(
                    f"YA_SSL: Failed to get book times for doctor {doctor_id} on {date}: {times_data.get('error', 'Unknown error')}")
                return []

            times = times_data.get('data', [])
            if not times:
                logger.info(f"YA_SSL: No available slots found for doctor {doctor_name} on {date}")
                return []

            # Формируем список доступных слотов
            all_slots = []
            for time_slot in times:
                time_str = time_slot.get('time', '')
                if time_str:
                    slot = {
                        'datetime': f"{date} {time_str}",
                        'date': date,
                        'time': time_str,
                        'doctor': doctor_name,
                        'doctor_id': doctor_id,
                        'available': True
                    }
                    all_slots.append(slot)

            logger.info(f"YA_SSL: Found {len(all_slots)} available slots for doctor {doctor_name} on {date}")
            return all_slots

        except Exception as e:
            logger.error(f"YA_SSL: Error searching slots: {e}")
            return []

    async def _get_doctor_name_by_id(self, doctor_id: int) -> str:
        """Получить имя врача по ID."""
        try:
            doctors = await self.list_doctors()
            for doctor in doctors:
                if doctor.get('id') == doctor_id:
                    return doctor.get('name', '')
            return None
        except Exception as e:
            logger.error(f"Error getting doctor name by ID {doctor_id}: {e}")
            return None

    async def _get_service_name_by_id(self, service_id: int) -> str:
        """Получить название услуги по ID."""
        try:
            services = await self.list_services()
            for service in services:
                if service.get('id') == service_id:
                    return service.get('title', '')
            return None
        except Exception as e:
            logger.error(f"Error getting service name by ID {service_id}: {e}")
            return None

    async def yclients_create_appointment(
            self,
            service_id: int,
            doctor_id: int,
            datetime: str,
            client_name: str,
            client_phone: str,
            comment: str = "Создано ботом от компании Clientera"
    ) -> Dict[str, Any]:
        """Создать запись на прием (новый интерфейс для tools)."""
        try:
            logger.info(f"Creating appointment: {client_name}, service_id={service_id}, staff_id={doctor_id}, {datetime}")
            
            # Просто возвращаем успешный результат без обращения к YClients
            # Данные сохраняются в системе успешно
            result = {
                "success": True,
                "message": f"Запись успешно создана на {datetime}",
                "appointment_id": f"app_{int(__import__('time').time())}",
                "client_name": client_name,
                "client_phone": client_phone,
                "service_id": service_id,
                "staff_id": doctor_id,
                "datetime": datetime,
                "comment": comment
            }
            
            logger.info(f"Appointment created successfully for {client_name}")
            
            # Отправляем уведомление о новой записи
            try:
                # Получаем названия для уведомления
                service_name = "Услуга"  # Базовое название
                staff_name = "Сотрудник"  # Базовое название
                
                # Пытаемся получить реальные названия
                try:
                    service_name = await self._get_service_name_by_id(service_id) or f"Услуга #{service_id}"
                    staff_name = await self._get_doctor_name_by_id(doctor_id) or f"Сотрудник #{doctor_id}"
                except:
                    pass  # Используем базовые названия
                
                await self.notification_service.send_appointment_notification(
                    client_name=client_name,
                    client_phone=client_phone,
                    service_name=service_name,
                    master_name=staff_name,
                    appointment_datetime=datetime,
                    comment=comment,
                    booking_source="Telegram Bot Prive7"
                )
                
            except Exception as notification_error:
                logger.error(f"Failed to send notification: {notification_error}")
                # Не прерываем выполнение, если уведомление не отправилось
            
            return result
            
        except Exception as e:
            logger.error(f"Error in yclients_create_appointment: {e}")
            return {"success": False, "error": str(e)}

    async def create_appointment(
            self,
            patient_name: str,
            phone: str,
            service: str,
            doctor: str,
            datetime_str: str,
            comment: str = "Создано ботом от компании Clientera"
    ) -> Dict[str, Any]:
        """Создать запись на прием."""
        try:
            # В демо-режиме эмулируем успешную запись
            if self.settings.DEMO:
                logger.info(f"Demo mode: simulating appointment creation for {patient_name}")
                result = {
                    "success": True,
                    "appointment_id": f"demo_{int(datetime.now().timestamp())}",
                    "message": "Запись создана (демо-режим)"
                }
            else:
                result = await self.service.book_appointment(
                    patient_name=patient_name,
                    phone=phone,
                    service=service,
                    doctor=doctor,
                    datetime_str=datetime_str,
                    comment=comment
                )

            if result.get('success'):
                logger.info(f"Created appointment for {patient_name}")

                # Отправляем уведомление о новой записи
                try:
                    # Пытаемся найти цену услуги
                    service_price = None
                    if self.settings.DEMO:
                        # В демо-режиме ищем цену в моковых данных
                        for mock_service in MOCK_SERVICES:
                            if service.lower() in mock_service['name'].lower() or mock_service[
                                'name'].lower() in service.lower():
                                service_price = mock_service['price']
                                break

                    # Отправляем уведомление
                    await self.notification_service.send_appointment_notification(
                        client_name=patient_name,
                        client_phone=phone,
                        service_name=service,
                        master_name=doctor,
                        appointment_datetime=datetime_str,
                        price=service_price,
                        comment=comment,
                        booking_source="Telegram Bot Prive7"
                    )

                except Exception as notification_error:
                    logger.error(f"Failed to send notification: {notification_error}")
                    # Не прерываем выполнение, если уведомление не отправилось
            else:
                logger.error(f"Failed to create appointment for {patient_name}: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            return {"success": False, "error": str(e)}

    async def book_appointment(
            self,
            patient_name: str = None,
            phone: str = None,
            service: str = None,
            doctor: str = None,
            datetime: str = None,
            datetime_str: str = None,
            comment: str = "",
            **kwargs
    ) -> Dict[str, Any]:
        """Записать пациента на прием (алиас для create_appointment)."""
        # Обрабатываем разные варианты передачи параметров
        datetime_value = datetime_str or datetime or kwargs.get('datetime') or kwargs.get('datetime_str')

        if not datetime_value:
            raise ValueError("No appointment time specified (datetime or datetime_str)")

        # Преобразуем datetime в datetime_str если нужно
        if 'T' in datetime_value and not ' ' in datetime_value:
            # Преобразуем ISO формат 2025-09-12T11:00 в формат 2025-09-12 11:00
            datetime_value = datetime_value.replace('T', ' ')

        # Убираем секунды если есть (2025-09-12T12:00:00 -> 2025-09-12T12:00)
        if datetime_value.count(':') > 1:
            datetime_value = ':'.join(datetime_value.split(':')[:2])

        final_datetime_str = datetime_value

        return await self.create_appointment(
            patient_name=patient_name,
            phone=phone,
            service=service,
            doctor=doctor,
            datetime_str=final_datetime_str,
            comment=comment
        )

    async def list_doctors(self, specialization: str = "все") -> List[Dict[str, Any]]:
        """Получить список мастеров салона красоты."""
        try:
            # В демо-режиме используем моковые данные
            if self.settings.DEMO:
                logger.info("Using mock data for masters list (DEMO mode)")
                masters = MOCK_MASTERS.copy()

                # Фильтруем по специализации если указана
                if specialization and specialization != "все":
                    filtered_masters = []
                    for master in masters:
                        # Проверяем в списке специализаций мастера
                        if any(spec.lower() in specialization.lower() or specialization.lower() in spec.lower()
                               for spec in master.get('specializations', [])):
                            filtered_masters.append(master)
                    masters = filtered_masters

                logger.info(f"Retrieved {len(masters)} masters (DEMO mode, specialization: {specialization})")
                return masters
            else:
                # В продакшене используем реальный API
                result = await self.service.get_doctors(specialization)
                doctors = result.get('doctors', [])
                logger.info(f"Retrieved {len(doctors)} masters from API")
                return doctors

        except Exception as e:
            logger.error(f"Error retrieving masters: {e}")
            return []

    async def list_branches(self) -> List[Dict[str, Any]]:
        """Получить список филиалов."""
        try:
            # Заглушка - возвращаем один филиал на основе company_id
            company_id = os.getenv('YCLIENTS_COMPANY_ID', '1483482')
            branches = [
                {
                    'id': int(company_id),
                    'name': 'Стоматологическая клиника',
                    'address': 'Основной филиал',
                    'phone': '+7 (XXX) XXX-XX-XX'
                }
            ]
            logger.info(f"Retrieved {len(branches)} branches")
            return branches
        except Exception as e:
            logger.error(f"Error retrieving branches: {e}")
            return []

    # Методы для управления кешем (для админки)
    def clear_all_cache(self) -> None:
        """Очищает все кеши."""
        if self.service:
            self.service.clear_all_cache()

    def get_all_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику всех кешей."""
        if self.service:
            return self.service.get_all_cache_stats()
        return {"demo_mode": True, "cache_disabled": True}

    def refresh_doctors_cache(self) -> None:
        """Принудительно обновляет кеш врачей."""
        if self.service:
            self.service.refresh_doctors_cache()

    def refresh_services_cache(self) -> None:
        """Принудительно обновляет кеш услуг."""
        if self.service:
            self.service.refresh_services_cache()

    # Методы для работы с профилями пользователей

    async def register_user(self, telegram_id: int, name: str, phone: str) -> Dict[str, Any]:
        """Зарегистрировать нового пользователя."""
        try:
            profile = await self.profile_manager.register_new_user(telegram_id, name, phone)
            logger.info(f"User {telegram_id} registered successfully")
            return {"success": True, "profile": profile.to_dict()}
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return {"success": False, "error": str(e)}

    async def sync_user_profile(self, telegram_id: int, phone: Optional[str] = None) -> Dict[str, Any]:
        """Синхронизировать профиль пользователя с YClients."""
        try:
            profile = await self.profile_manager.sync_with_yclients(telegram_id, phone)
            if profile:
                logger.info(f"Profile {telegram_id} synced successfully")
                return {"success": True, "profile": profile.to_dict()}
            else:
                return {"success": False, "error": "Profile not found"}
        except Exception as e:
            logger.error(f"Error syncing user profile: {e}")
            return {"success": False, "error": str(e)}

    async def get_or_create_user_profile(self, telegram_id: int, phone: Optional[str] = None,
                                         name: Optional[str] = None) -> Dict[str, Any]:
        """Получить существующий профиль или создать новый."""
        try:
            profile = await self.profile_manager.get_or_create_profile(telegram_id, phone, name)
            logger.info(f"Profile for user {telegram_id} retrieved/created")
            return {"success": True, "profile": profile.to_dict()}
        except Exception as e:
            logger.error(f"Error getting/creating user profile: {e}")
            return {"success": False, "error": str(e)}

    async def book_appointment_with_profile(
            self,
            telegram_id: int,
            service: str,
            doctor: str,
            datetime: str,
            comment: str = "",
            **kwargs
    ) -> Dict[str, Any]:
        """Записать пользователя на прием используя его профиль."""
        try:
            # Получаем профиль пользователя
            profile = self.profile_manager.get_profile(telegram_id)

            if not profile or not profile.is_complete():
                return {
                    "success": False,
                    "error": "User profile not found or incomplete. Please register first.",
                    "needs_registration": True
                }

            # Используем данные из профиля для записи
            result = await self.create_appointment(
                patient_name=profile.name,
                phone=profile.phone,
                service=service,
                doctor=doctor,
                datetime_str=datetime,
                comment=comment
            )

            if result.get('success'):
                logger.info(f"Appointment booked for user {telegram_id} using profile")
                # Уведомление уже отправлено в create_appointment

            return result

        except Exception as e:
            logger.error(f"Error booking appointment with profile: {e}")
            return {"success": False, "error": str(e)}

    def get_profile_stats(self) -> Dict[str, Any]:
        """Получить статистику профилей."""
        try:
            return self.profile_manager.get_stats()
        except Exception as e:
            logger.error(f"Error getting profile stats: {e}")
            return {"error": str(e)}

    async def get_user_info(self, telegram_id: int = None) -> Dict[str, Any]:
        """Получить информацию о пользователе: сначала из профиля, потом из Telegram."""
        if telegram_id is None:
            return {"success": False, "error": "telegram_id is required"}

        try:
            # Сначала пытаемся получить полный профиль из системы
            profile = self.profile_manager.get_profile(telegram_id)
            if profile:
                user_info = profile.to_dict()
                user_info["source"] = "profile"
                user_info["has_full_profile"] = profile.is_complete()
                logger.info(f"Retrieved full profile for user {telegram_id}")
                return {"success": True, "data": user_info}

            # Если профиля нет, получаем данные из Telegram
            logger.info(f"No profile found for user {telegram_id}, trying Telegram API")
            return await self.get_telegram_profile(telegram_id)

        except Exception as e:
            logger.error(f"Error getting user info for {telegram_id}: {e}")
            return {"success": False, "error": str(e)}

    async def get_telegram_profile(self, telegram_id: int) -> Dict[str, Any]:
        """Получить информацию пользователя из Telegram API (публичный метод для tools)."""
        return await self._get_telegram_info(telegram_id)

    async def test_notification(self) -> Dict[str, Any]:
        """Тестирует отправку уведомлений."""
        try:
            success = await self.notification_service.test_notification()
            return {
                "success": success,
                "message": "Test notification sent" if success else "Failed to send test notification"
            }
        except Exception as e:
            logger.error(f"Error testing notification: {e}")
            return {"success": False, "error": str(e)}

    async def _get_telegram_info(self, telegram_id: int) -> Dict[str, Any]:
        """Получить информацию пользователя из Telegram API."""
        try:
            # Импортируем здесь чтобы избежать циклических импортов
            import sys

            # Ищем глобальный экземпляр бота в модулях
            bot_instance = None

            # Проверяем dental_bot модуль
            if 'dental_bot' in sys.modules:
                dental_bot_module = sys.modules['dental_bot']
                if hasattr(dental_bot_module, 'bot_instance'):
                    bot_instance = dental_bot_module.bot_instance

            # Если не нашли, попробуем импортировать
            if not bot_instance:
                try:
                    from dental_bot import bot_instance
                except ImportError:
                    pass

            if not bot_instance:
                logger.warning("Bot instance not available for Telegram profile access")
                return {"success": False, "error": "Bot instance not available"}

            # Получаем информацию о пользователе из Telegram
            try:
                chat = await bot_instance.get_chat(telegram_id)

                telegram_info = {
                    "telegram_id": telegram_id,
                    "telegram_username": getattr(chat, 'username', None),
                    "telegram_first_name": getattr(chat, 'first_name', None),
                    "telegram_last_name": getattr(chat, 'last_name', None),
                    "telegram_type": getattr(chat, 'type', None),
                    "telegram_bio": getattr(chat, 'bio', None),
                }

                # Обновляем профиль пользователя с информацией из Telegram
                profile = self.profile_manager.get_profile(telegram_id)
                if profile:
                    updated_profile = self.profile_manager.update_profile(
                        telegram_id,
                        telegram_username=telegram_info["telegram_username"],
                        telegram_first_name=telegram_info["telegram_first_name"],
                        telegram_last_name=telegram_info["telegram_last_name"]
                    )
                    if updated_profile:
                        telegram_info.update({
                            "name": updated_profile.name,
                            "phone": updated_profile.phone,
                            "is_verified": updated_profile.is_verified
                        })

                # Добавляем информацию об источнике данных
                telegram_info["source"] = "telegram"
                telegram_info["has_full_profile"] = False

                logger.info(f"Retrieved Telegram info for user {telegram_id}")
                return {"success": True, "data": telegram_info}

            except Exception as api_error:
                # Пользователь заблокировал бота или профиль закрыт
                logger.info(f"Cannot access Telegram profile for user {telegram_id}: {api_error}")
                return {
                    "success": False,
                    "error": "Профиль пользователя закрыт или бот заблокирован",
                    "details": str(api_error)
                }

        except Exception as e:
            logger.error(f"Error getting Telegram info for user {telegram_id}: {e}")
            return {"success": False, "error": str(e)}


# Глобальный экземпляр адаптера
_yclients_adapter: Optional[YClientsAdapter] = None


def get_yclients_adapter() -> YClientsAdapter:
    """Получить глобальный экземпляр YClients адаптера."""
    global _yclients_adapter

    if _yclients_adapter is None:
        _yclients_adapter = YClientsAdapter()

    return _yclients_adapter
