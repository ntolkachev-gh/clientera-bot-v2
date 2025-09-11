#!/usr/bin/env python3
"""
Тест YClients адаптера
"""

import asyncio
import json
import logging
import os
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Импортируем наш класс из dental_bot.py
import sys
sys.path.append('..')

from dental_bot import YClientsIntegration

async def test_adapter():
    """Тестируем все методы адаптера"""
    
    logger.info("🚀 Начинаем тестирование YClients адаптера...")
    
    try:
        # Инициализируем адаптер
        adapter = YClientsIntegration()
        
        # 1. Тест получения услуг
        logger.info("\n📋 1. Тестируем получение услуг...")
        services = await adapter.get_services()
        logger.info(f"Получено услуг: {len(services.get('services', []))}")
        if services.get('services'):
            for i, service in enumerate(services['services'][:3]):  # Показываем первые 3
                logger.info(f"   {i+1}. {service['name']} ({service['price_from']}-{service['price_to']}₽)")
        
        # 2. Тест получения врачей
        logger.info("\n👨‍⚕️ 2. Тестируем получение врачей...")
        doctors = await adapter.get_doctors()
        logger.info(f"Получено врачей: {len(doctors.get('doctors', []))}")
        if doctors.get('doctors'):
            for i, doctor in enumerate(doctors['doctors'][:3]):  # Показываем первых 3
                logger.info(f"   {i+1}. {doctor['name']} ({doctor['specialization']})")
        
        # 3. Тест получения врачей по специализации
        logger.info("\n🔍 3. Тестируем поиск врачей по специализации (ортодонт)...")
        ortodont_doctors = await adapter.get_doctors("ортодонт")
        logger.info(f"Найдено ортодонтов: {len(ortodont_doctors.get('doctors', []))}")
        
        # 4. Тест поиска слотов
        logger.info("\n📅 4. Тестируем поиск свободных слотов...")
        try:
            slots = await adapter.search_appointments("Консультация", "Морозов", "2024-12-10")
            logger.info(f"Найдено слотов: {len(slots.get('appointments', []))}")
            if slots.get('appointments'):
                for i, slot in enumerate(slots['appointments'][:2]):  # Показываем первые 2
                    logger.info(f"   {i+1}. {slot['datetime']} - {slot['doctor']}")
        except Exception as e:
            logger.warning(f"⚠️ Поиск слотов: {e}")
        
        # 5. Тест записи на прием
        logger.info("\n📝 5. Тестируем запись на прием...")
        try:
            booking = await adapter.book_appointment(
                patient_name="Тестовый Пациент",
                phone="+79001234567", 
                service="Консультация стоматолога",
                doctor="Морозов",
                datetime_str="2024-12-10 14:00",
                comment="Тестовая запись"
            )
            logger.info(f"Запись создана: {booking.get('message', 'OK')}")
        except Exception as e:
            logger.warning(f"⚠️ Запись на прием: {e}")
        
        logger.info("\n🎉 Тестирование завершено успешно!")
        
    except Exception as e:
        logger.error(f" Критическая ошибка тестирования: {e}")

if __name__ == "__main__":
    asyncio.run(test_adapter())
