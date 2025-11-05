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

# DEMO режим удален. Все методы используют реальные вызовы YClients API.


class YClientsAdapter:
    """Adapter для YClients API для использования в Realtime API."""

    def __init__(self):
        """Инициализация адаптера."""
        self.settings = get_settings()

        # Всегда инициализируем реальный сервис YClients
        self.service = get_yclients_service()

        self.profile_manager = get_profile_manager()
        self.notification_service = get_notification_service()

        mode = "DEMO" if self.settings.DEMO else "PRODUCTION"
        logger.info(f"YClients Adapter initialized in {mode} mode")

    async def list_services(self, category: str = "все", limit: int = 50) -> List[Dict[str, Any]]:
        """Получить список услуг."""
        try:
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
            doctor_id: int = None,
            date: str = None,
            master_id: int = None
    ) -> List[Dict[str, Any]]:
        """Найти свободные слоты для записи на услугу для конкретного врача на конкретную дату."""
        try:
            # Поддерживаем оба поля для обратной совместимости: doctor_id и master_id
            target_id = master_id if master_id is not None else doctor_id
            logger.info(f"YA_SSL: Searching slots for master_id={target_id}, date={date}")
            # Получаем имя врача по ID
            doctor_name = None
            doctors_result = await self.service.get_doctors()
            for doctor in doctors_result.get('doctors', []):
                if doctor.get('id') == target_id:
                    doctor_name = doctor.get('name', '')
                    break

            if not doctor_name:
                logger.warning(f"YA_SSL: Master with ID {target_id} not found")
                return []

            # Получаем доступные слоты напрямую через API без привязки к конкретной услуге
            # API endpoint: /book_times/{company_id}/{staff_id}/{date}
            times_data = await self.service.api.get_book_times(target_id, date)

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
                        'doctor': doctor_name,  # backward compatibility
                        'doctor_id': target_id,  # backward compatibility
                        'master': doctor_name,
                        'master_id': target_id,
                        'available': True
                    }
                    all_slots.append(slot)

            logger.info(f"YA_SSL: Found {len(all_slots)} available slots for master {doctor_name} on {date}")
            return all_slots

        except Exception as e:
            logger.error(f"YA_SSL: Error searching slots: {e}")
            return []

    async def _get_master_name_by_id(self, master_id: int) -> str:
        """Получить имя мастера по ID."""
        try:
            masters = await self.list_masters()
            for master in masters:
                if master.get('id') == master_id:
                    return master.get('name', '')
            return None
        except Exception as e:
            logger.error(f"Error getting master name by ID {master_id}: {e}")
            return None

    async def _get_doctor_name_by_id(self, doctor_id: int) -> str:
        """Алиас для совместимости: получить имя мастера по ID (doctor_id)."""
        return await self._get_master_name_by_id(doctor_id)

    async def _get_service_name_by_id(self, service_id: int) -> str:
        """Получить название услуги по ID."""
        try:
            services = await self.list_services()
            for service in services:
                if service.get('id') == service_id:
                    return service.get('name', '')
            return None
        except Exception as e:
            logger.error(f"Error getting service name by ID {service_id}: {e}")
            return None

    async def yclients_create_appointment(
            self,
            service_id: int,
            datetime: str,
            client_name: str,
            client_phone: str,
            doctor_id: int = None,
            master_id: int = None,
            comment: str = "Создано ботом от компании Clientera"
    ) -> Dict[str, Any]:
        """Создать запись на прием (прямой вызов YClients по ID услуг/сотрудника)."""
        try:
            target_id = master_id if master_id is not None else doctor_id
            logger.info(f"Creating appointment: {client_name}, service_id={service_id}, staff_id={target_id}, {datetime}")

            # Найти или создать клиента
            client_result = await self.service.api.find_or_create_client(client_name, client_phone)
            if not client_result.get('success'):
                return {"success": False, "error": client_result.get('error', 'Failed to find/create client')}

            client_data = client_result.get('data', {})
            client_email = client_data.get('email') or ""

            # Преобразуем дату/время
            try:
                dt = datetime.strptime(datetime, "%Y-%m-%d %H:%M")
                date_str = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M")
            except ValueError:
                return {"success": False, "error": f"Invalid date/time format: {datetime}"}

            record_data = {
                "company_id": int(self.service.api.company_id),
                "name": client_name,
                "phone": client_phone,
                "email": client_email,
                "fullname": client_name,
                "appointments": [{
                    "id": 1,
                    "services": [service_id],
                    "staff_id": target_id,
                    "datetime": f"{date_str}T{time_str}:00+03:00"
                }],
                "comment": comment or "Запись через бота"
            }

            result = await self.service.api.create_record(record_data)

            if result.get('success'):
                # Отправляем уведомление
                try:
                    service_name = await self._get_service_name_by_id(service_id) or f"Услуга #{service_id}"
                    staff_name = await self._get_master_name_by_id(target_id) or f"Сотрудник #{target_id}"

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

                return {
                    "success": True,
                    "message": f"Запись успешно создана на {datetime}",
                    "record_id": (result.get('data') or {}).get('id') if isinstance(result.get('data'), dict) else None,
                    "client_name": client_name,
                    "client_phone": client_phone,
                    "service_id": service_id,
                    "staff_id": target_id,
                    "datetime": datetime
                }

            return {"success": False, "error": result.get('error', 'Unknown error')}

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
            master: Optional[str] = None,
            comment: str = "Создано ботом от компании Clientera"
    ) -> Dict[str, Any]:
        """Создать запись на прием."""
        try:
            # Поддержка алиаса: если передан master, используем его как имя специалиста
            doctor_name = doctor or master
            result = await self.service.book_appointment(
                patient_name=patient_name,
                phone=phone,
                service=service,
                doctor=doctor_name,
                datetime_str=datetime_str,
                comment=comment
            )

            if result.get('success'):
                logger.info(f"Created appointment for {patient_name}")

                # Отправляем уведомление о новой записи
                try:
                    await self.notification_service.send_appointment_notification(
                        client_name=patient_name,
                        client_phone=phone,
                        service_name=service,
                        master_name=doctor_name,
                        appointment_datetime=datetime_str,
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
            master: str = None,
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
            master=master or kwargs.get('master'),
            datetime_str=final_datetime_str,
            comment=comment
        )

    async def list_masters(self, specialization: str = "все") -> List[Dict[str, Any]]:
        """Получить список мастеров салона красоты (masters)."""
        try:
            result = await self.service.get_doctors(specialization)
            masters = result.get('doctors', [])
            logger.info(f"Retrieved {len(masters)} masters from API")
            return masters

        except Exception as e:
            logger.error(f"Error retrieving masters: {e}")
            return []

    async def list_doctors(self, specialization: str = "все") -> List[Dict[str, Any]]:
        """Алиас для совместимости: получить список мастеров (doctors)."""
        return await self.list_masters(specialization)

    async def list_branches(self) -> List[Dict[str, Any]]:
        """Получить список филиалов."""
        try:
            # Получаем информацию о компании из YClients
            company_info = await self.service.api.get_company_info()
            branches: List[Dict[str, Any]] = []
            if company_info.get('success') and company_info.get('data'):
                data = company_info['data']
                branches.append({
                    'id': int(self.service.api.company_id),
                    'name': data.get('title') or data.get('name') or 'Компания',
                    'address': data.get('address') or '',
                    'phone': data.get('phone') or ''
                })
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
            # Поддерживаем алиас master через kwargs
            result = await self.create_appointment(
                patient_name=profile.name,
                phone=profile.phone,
                service=service,
                doctor=doctor or kwargs.get('master'),
                master=kwargs.get('master'),
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
