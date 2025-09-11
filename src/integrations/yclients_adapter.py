"""
YClients API adapter for Realtime API integration.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .yclients_service import get_yclients_service
from .user_profiles import get_profile_manager, UserProfile
from ..utils.logger import get_logger

logger = get_logger(__name__)


class YClientsAdapter:
    """Adapter для YClients API для использования в Realtime API."""
    
    def __init__(self):
        """Инициализация адаптера."""
        self.service = get_yclients_service()
        self.profile_manager = get_profile_manager()
        
        logger.info("YClients Adapter initialized")
    
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
        doctor_id: int,
        date: str
    ) -> List[Dict[str, Any]]:
        """Найти свободные слоты для записи на услугу для конкретного врача на конкретную дату."""
        try:
            logger.info(f"Searching slots for doctor_id={doctor_id}, date={date}")
            
            # Получаем имя врача по ID
            doctor_name = None
            doctors_result = await self.service.get_doctors()
            for doctor in doctors_result.get('doctors', []):
                if doctor.get('id') == doctor_id:
                    doctor_name = doctor.get('name', '')
                    break
            
            if not doctor_name:
                logger.warning(f"Doctor with ID {doctor_id} not found")
                return []
            
            # Получаем доступные слоты напрямую через API без привязки к конкретной услуге
            # API endpoint: /book_times/{company_id}/{staff_id}/{date}
            times_data = await self.service.api.get_book_times(doctor_id, date)
            
            if not times_data.get('success'):
                logger.warning(f"Failed to get book times for doctor {doctor_id} on {date}: {times_data.get('error', 'Unknown error')}")
                return []
            
            times = times_data.get('data', [])
            if not times:
                logger.info(f"No available slots found for doctor {doctor_name} on {date}")
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
            logger.error(f"Error searching slots: {e}")
            return []
    
    
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
        """Получить список врачей."""
        try:
            result = await self.service.get_doctors(specialization)
            doctors = result.get('doctors', [])
            logger.info(f"Retrieved {len(doctors)} doctors")
            return doctors
        except Exception as e:
            logger.error(f"Error retrieving doctors: {e}")
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
        self.service.clear_all_cache()
    
    def get_all_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику всех кешей."""
        return self.service.get_all_cache_stats()
    
    def refresh_doctors_cache(self) -> None:
        """Принудительно обновляет кеш врачей."""
        self.service.refresh_doctors_cache()
    
    def refresh_services_cache(self) -> None:
        """Принудительно обновляет кеш услуг."""
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
    
    async def get_or_create_user_profile(self, telegram_id: int, phone: Optional[str] = None, name: Optional[str] = None) -> Dict[str, Any]:
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
            return await self._get_telegram_info(telegram_id)
            
        except Exception as e:
            logger.error(f"Error getting user info for {telegram_id}: {e}")
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
