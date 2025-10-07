"""
Сервис для отправки уведомлений о записях в другой Telegram бот.
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime

from ..config.env import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений о записях."""
    
    def __init__(self):
        """Инициализация сервиса уведомлений."""
        self.settings = get_settings()
        self.bot_token = self.settings.NOTIFICATION_BOT_TOKEN
        
        # Собираем все chat_id из разных источников
        self.chat_ids = []
        
        # Одиночный chat_id
        if self.settings.NOTIFICATION_CHAT_ID:
            self.chat_ids.append(self.settings.NOTIFICATION_CHAT_ID.strip())
        
        # Множественные chat_id (разделенные запятыми)
        if self.settings.NOTIFICATION_CHAT_IDS:
            multiple_ids = [
                chat_id.strip() 
                for chat_id in self.settings.NOTIFICATION_CHAT_IDS.split(',') 
                if chat_id.strip()
            ]
            self.chat_ids.extend(multiple_ids)
        
        # Удаляем дубликаты
        self.chat_ids = list(set(self.chat_ids))
        
        if self.bot_token and self.chat_ids:
            logger.info(f"Notification service initialized for {len(self.chat_ids)} recipients")
            logger.debug(f"Recipients: {self.chat_ids}")
        else:
            logger.warning("Notification service disabled - missing token or chat_ids")
    
    def is_enabled(self) -> bool:
        """Проверяет, включен ли сервис уведомлений."""
        return bool(self.bot_token and self.chat_ids)
    
    async def send_appointment_notification(
        self,
        client_name: str,
        client_phone: str,
        service_name: str,
        master_name: str,
        appointment_datetime: str,
        price: Optional[float] = None,
        comment: str = "",
        booking_source: str = "Telegram Bot"
    ) -> bool:
        """
        Отправляет уведомление о новой записи.
        
        Args:
            client_name: Имя клиента
            client_phone: Телефон клиента
            service_name: Название услуги
            master_name: Имя мастера
            appointment_datetime: Дата и время записи
            price: Стоимость услуги (опционально)
            comment: Комментарий к записи
            booking_source: Источник записи
            
        Returns:
            bool: True если уведомление отправлено успешно
        """
        if not self.is_enabled():
            logger.debug("Notification service disabled, skipping notification")
            return False
        
        try:
            # Формируем текст уведомления
            message_text = self._format_notification_message(
                client_name=client_name,
                client_phone=client_phone,
                service_name=service_name,
                master_name=master_name,
                appointment_datetime=appointment_datetime,
                price=price,
                comment=comment,
                booking_source=booking_source
            )
            
            # Отправляем уведомление всем получателям
            success_count = 0
            total_recipients = len(self.chat_ids)
            
            for chat_id in self.chat_ids:
                success = await self._send_telegram_message(message_text, chat_id)
                if success:
                    success_count += 1
                else:
                    logger.error(f"Failed to send notification to {chat_id}")
            
            if success_count > 0:
                logger.info(f"Notification sent for appointment: {client_name} - {service_name} "
                          f"({success_count}/{total_recipients} recipients)")
            else:
                logger.error(f"Failed to send notification to any recipient for appointment: {client_name} - {service_name}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending appointment notification: {e}")
            return False
    
    def _format_notification_message(
        self,
        client_name: str,
        client_phone: str,
        service_name: str,
        master_name: str,
        appointment_datetime: str,
        price: Optional[float] = None,
        comment: str = "",
        booking_source: str = "Telegram Bot"
    ) -> str:
        """Форматирует текст уведомления о записи."""
        
        # Основная информация
        message_lines = [
            "🆕 <b>НОВАЯ ЗАПИСЬ</b>",
            "",
            f"👤 <b>Клиент:</b> {client_name}",
            f"📱 <b>Телефон:</b> {client_phone}",
            "",
            f"💅 <b>Услуга:</b> {service_name}",
            f"👩‍💼 <b>Мастер:</b> {master_name}",
            f"📅 <b>Дата и время:</b> {appointment_datetime}",
        ]
        
        # Добавляем цену если указана
        if price:
            message_lines.append(f"💰 <b>Стоимость:</b> {price:,.0f} ₽")
        
        # Добавляем комментарий если есть
        if comment and comment.strip():
            message_lines.extend([
                "",
                f"💬 <b>Комментарий:</b> {comment}"
            ])
        
        # Добавляем информацию об источнике и времени
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
        message_lines.extend([
            "",
            f"📲 <b>Источник:</b> {booking_source}",
            f"🕐 <b>Время записи:</b> {current_time}"
        ])
        
        return "\n".join(message_lines)
    
    async def _send_telegram_message(self, text: str, chat_id: str) -> bool:
        """Отправляет сообщение через Telegram Bot API."""
        if not self.bot_token or not chat_id:
            return False
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            return True
                        else:
                            logger.error(f"Telegram API error: {result.get('description', 'Unknown error')}")
                            logger.debug(f"Full response: {result}")
                            return False
                    else:
                        logger.error(f"HTTP error {response.status} when sending notification")
                        logger.debug(f"Response body: {response_text}")
                        try:
                            error_data = await response.json()
                            logger.error(f"Error details: {error_data}")
                        except:
                            pass
                        return False
                        
        except asyncio.TimeoutError:
            logger.error("Timeout when sending notification")
            return False
        except Exception as e:
            logger.error(f"Exception when sending notification: {e}")
            return False
    
    async def test_notification(self) -> bool:
        """Отправляет тестовое уведомление для проверки работы сервиса."""
        if not self.is_enabled():
            logger.warning("Cannot test notification - service disabled")
            return False
        
        test_message = (
            "🧪 <b>ТЕСТОВОЕ УВЕДОМЛЕНИЕ</b>\n\n"
            "Сервис уведомлений о записях работает корректно!\n\n"
            f"🕐 Время теста: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"📊 Получателей: {len(self.chat_ids)}"
        )
        
        success_count = 0
        total_recipients = len(self.chat_ids)
        
        for chat_id in self.chat_ids:
            success = await self._send_telegram_message(test_message, chat_id)
            if success:
                success_count += 1
            else:
                logger.error(f"Failed to send test notification to {chat_id}")
        
        if success_count > 0:
            logger.info(f"Test notification sent successfully ({success_count}/{total_recipients} recipients)")
        else:
            logger.error("Failed to send test notification to any recipient")
        
        return success_count > 0


# Глобальный экземпляр сервиса уведомлений
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Получить глобальный экземпляр сервиса уведомлений."""
    global _notification_service
    
    if _notification_service is None:
        _notification_service = NotificationService()
    
    return _notification_service
