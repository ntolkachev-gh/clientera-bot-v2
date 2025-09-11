"""
Система профилей пользователей с интеграцией YClients.
Автоматически получает и кэширует информацию о пользователях из YClients.
"""

import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import asyncio

from .yclients_service import get_yclients_service
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class UserProfile:
    """Профиль пользователя."""
    telegram_id: int
    yclients_id: Optional[int] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[str] = None
    sex_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_synced: Optional[str] = None
    is_verified: bool = False
    # Дополнительная информация из Telegram
    telegram_username: Optional[str] = None
    telegram_first_name: Optional[str] = None
    telegram_last_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует профиль в словарь."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Создает профиль из словаря."""
        return cls(**data)
    
    def is_complete(self) -> bool:
        """Проверяет, заполнен ли профиль полностью."""
        return bool(self.name and self.phone and self.yclients_id)
    
    def needs_sync(self, sync_interval_hours: int = 24) -> bool:
        """Проверяет, нужно ли синхронизировать профиль с YClients."""
        if not self.last_synced:
            return True
        
        last_sync = datetime.fromisoformat(self.last_synced)
        return datetime.now() - last_sync > timedelta(hours=sync_interval_hours)


class UserProfileManager:
    """Менеджер профилей пользователей."""
    
    def __init__(self, cache_file: str = "user_profiles.json"):
        """Инициализация менеджера профилей."""
        self.cache_file = cache_file
        self.profiles: Dict[int, UserProfile] = {}
        self.service = get_yclients_service()
        self.api = self.service.api  # Используем API с настроенным user_token
        self._load_profiles()
        
        # Диагностика user_token
        if self.api.user_token:
            logger.info(f"✅ UserProfileManager инициализирован с user_token: {self.api.user_token[:10]}...")
        else:
            logger.warning("⚠️ UserProfileManager инициализирован БЕЗ user_token - могут быть проблемы с созданием клиентов")
        
        logger.info(f"Инициализирован менеджер профилей, загружено {len(self.profiles)} профилей")
    
    async def _update_telegram_info(self, telegram_id: int) -> None:
        """Обновляет профиль информацией из Telegram."""
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
            
            if not bot_instance:
                return
            
            # Получаем информацию о пользователе из Telegram
            try:
                chat = await bot_instance.get_chat(telegram_id)
                
                self.update_profile(
                    telegram_id,
                    telegram_username=getattr(chat, 'username', None),
                    telegram_first_name=getattr(chat, 'first_name', None),
                    telegram_last_name=getattr(chat, 'last_name', None)
                )
                logger.info(f"Updated profile {telegram_id} with Telegram info")
                
            except Exception as api_error:
                logger.debug(f"Cannot access Telegram profile for user {telegram_id}: {api_error}")
                
        except Exception as e:
            logger.debug(f"Error updating Telegram info for user {telegram_id}: {e}")
    
    def _load_profiles(self) -> None:
        """Загружает профили из файла."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.profiles = {
                        int(telegram_id): UserProfile.from_dict(profile_data)
                        for telegram_id, profile_data in data.items()
                    }
                logger.info(f"Загружено {len(self.profiles)} профилей из {self.cache_file}")
            except Exception as e:
                logger.error(f"Ошибка загрузки профилей: {e}")
                self.profiles = {}
        else:
            logger.info(f"Файл профилей {self.cache_file} не найден, создаем новый")
    
    def _save_profiles(self) -> None:
        """Сохраняет профили в файл."""
        try:
            data = {
                str(telegram_id): profile.to_dict()
                for telegram_id, profile in self.profiles.items()
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Сохранено {len(self.profiles)} профилей в {self.cache_file}")
        except Exception as e:
            logger.error(f"Ошибка сохранения профилей: {e}")
    
    def get_profile(self, telegram_id: int) -> Optional[UserProfile]:
        """Получает профиль пользователя."""
        return self.profiles.get(telegram_id)
    
    def create_profile(self, telegram_id: int, **kwargs) -> UserProfile:
        """Создает новый профиль пользователя."""
        profile = UserProfile(telegram_id=telegram_id, **kwargs)
        profile.created_at = datetime.now().isoformat()
        profile.updated_at = profile.created_at
        
        self.profiles[telegram_id] = profile
        self._save_profiles()
        
        logger.info(f"Создан новый профиль для пользователя {telegram_id}")
        return profile
    
    def update_profile(self, telegram_id: int, **kwargs) -> Optional[UserProfile]:
        """Обновляет профиль пользователя."""
        profile = self.profiles.get(telegram_id)
        if not profile:
            return None
        
        # Обновляем поля
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.updated_at = datetime.now().isoformat()
        self._save_profiles()
        
        logger.info(f"Обновлен профиль пользователя {telegram_id}")
        return profile
    
    async def sync_with_yclients(self, telegram_id: int, phone: Optional[str] = None) -> Optional[UserProfile]:
        """Синхронизирует профиль с YClients."""
        profile = self.profiles.get(telegram_id)
        
        # Определяем телефон для поиска
        search_phone = phone or (profile.phone if profile else None)
        if not search_phone:
            logger.warning(f"Нет телефона для синхронизации профиля {telegram_id}")
            return profile
        
        try:
            # Ищем клиента в YClients
            search_result = await self.api.find_or_create_client("", search_phone)
            
            if search_result.get('success') and search_result.get('data'):
                yclients_data = search_result['data']
                
                # Обновляем или создаем профиль
                if profile:
                    profile.yclients_id = yclients_data.get('id')
                    profile.name = yclients_data.get('name') or profile.name
                    profile.phone = yclients_data.get('phone') or profile.phone
                    profile.email = yclients_data.get('email') or profile.email
                    profile.birth_date = yclients_data.get('birth_date') or profile.birth_date
                    profile.sex_id = yclients_data.get('sex_id') or profile.sex_id
                    profile.is_verified = True
                    profile.last_synced = datetime.now().isoformat()
                    profile.updated_at = profile.last_synced
                else:
                    profile = self.create_profile(
                        telegram_id=telegram_id,
                        yclients_id=yclients_data.get('id'),
                        name=yclients_data.get('name'),
                        phone=yclients_data.get('phone'),
                        email=yclients_data.get('email'),
                        birth_date=yclients_data.get('birth_date'),
                        sex_id=yclients_data.get('sex_id'),
                        is_verified=True,
                        last_synced=datetime.now().isoformat()
                    )
                
                self.profiles[telegram_id] = profile
                self._save_profiles()
                
                logger.info(f"Профиль {telegram_id} синхронизирован с YClients (ID: {profile.yclients_id})")
                return profile
            else:
                logger.info(f"Клиент с телефоном {search_phone} не найден в YClients")
                return profile
                
        except Exception as e:
            logger.error(f"Ошибка синхронизации профиля {telegram_id}: {e}")
            return profile
    
    async def get_or_create_profile(self, telegram_id: int, phone: Optional[str] = None, name: Optional[str] = None) -> UserProfile:
        """Получает существующий профиль или создает новый с синхронизацией YClients."""
        profile = self.get_profile(telegram_id)
        
        # Если профиля нет, создаем базовый
        if not profile:
            profile = self.create_profile(telegram_id=telegram_id, phone=phone, name=name)
            
            # Пытаемся получить дополнительную информацию из Telegram
            try:
                await self._update_telegram_info(telegram_id)
            except Exception as e:
                logger.debug(f"Could not get Telegram info for profile {telegram_id}: {e}")
        
        # Синхронизируем с YClients если есть телефон и нужна синхронизация
        if phone or (profile.phone and profile.needs_sync()):
            synced_profile = await self.sync_with_yclients(telegram_id, phone or profile.phone)
            if synced_profile:
                profile = synced_profile
        
        return profile
    
    async def register_new_user(self, telegram_id: int, name: str, phone: str) -> UserProfile:
        """Регистрирует нового пользователя в системе."""
        logger.info(f"Регистрация нового пользователя {telegram_id}: {name}, {phone}")
        
        # Проверяем наличие user_token
        if not self.api.user_token:
            logger.warning("⚠️ Нет user_token для создания клиента в YClients")
        
        try:
            # Создаем клиента в YClients
            client_data = {
                "name": name,
                "phone": phone,
                "sex_id": 0  # Не указано
            }
            
            logger.debug(f"Создаем клиента в YClients с данными: {client_data}")
            create_result = await self.api.create_client(client_data)
            
            if create_result.get('success'):
                yclients_data = create_result['data']
                
                # Создаем профиль с данными из YClients
                profile = self.create_profile(
                    telegram_id=telegram_id,
                    yclients_id=yclients_data.get('id'),
                    name=yclients_data.get('name', name),
                    phone=yclients_data.get('phone', phone),
                    email=yclients_data.get('email'),
                    birth_date=yclients_data.get('birth_date'),
                    sex_id=yclients_data.get('sex_id'),
                    is_verified=True,
                    last_synced=datetime.now().isoformat()
                )
                
                logger.info(f"Пользователь {telegram_id} успешно зарегистрирован в YClients (ID: {profile.yclients_id})")
                return profile
            else:
                # Если не удалось создать в YClients (например, уже существует), пытаемся найти
                logger.warning(f"Не удалось создать клиента в YClients: {create_result.get('error')}")
                profile = await self.sync_with_yclients(telegram_id, phone)
                
                if not profile or not profile.yclients_id:
                    # Создаем локальный профиль без YClients ID
                    profile = self.create_profile(
                        telegram_id=telegram_id,
                        name=name,
                        phone=phone,
                        is_verified=False
                    )
                
                return profile
                
        except Exception as e:
            logger.error(f"Ошибка регистрации пользователя {telegram_id}: {e}")
            
            # Создаем локальный профиль в случае ошибки
            profile = self.create_profile(
                telegram_id=telegram_id,
                name=name,
                phone=phone,
                is_verified=False
            )
            
            return profile
    
    def get_all_profiles(self) -> List[UserProfile]:
        """Получает все профили."""
        return list(self.profiles.values())
    
    def delete_profile(self, telegram_id: int) -> bool:
        """Удаляет профиль пользователя."""
        if telegram_id in self.profiles:
            del self.profiles[telegram_id]
            self._save_profiles()
            logger.info(f"Профиль пользователя {telegram_id} удален")
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Получает статистику профилей."""
        total = len(self.profiles)
        verified = sum(1 for p in self.profiles.values() if p.is_verified)
        complete = sum(1 for p in self.profiles.values() if p.is_complete())
        
        return {
            "total_profiles": total,
            "verified_profiles": verified,
            "complete_profiles": complete,
            "verification_rate": round(verified / total * 100, 1) if total > 0 else 0,
            "completion_rate": round(complete / total * 100, 1) if total > 0 else 0
        }


# Глобальный экземпляр менеджера профилей
_profile_manager: Optional[UserProfileManager] = None


def get_profile_manager() -> UserProfileManager:
    """Получить глобальный экземпляр менеджера профилей."""
    global _profile_manager
    
    if _profile_manager is None:
        _profile_manager = UserProfileManager()
    
    return _profile_manager
