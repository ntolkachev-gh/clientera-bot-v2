#!/usr/bin/env python3
"""
Tool schemas and constants for YCLIENTS integration.
"""

from typing import Dict, List, Any

from .events import Tool
from ..config.env import get_settings

# YCLIENTS tool schemas
YCLIENTS_TOOLS: List[Tool] = [
    Tool(
        name="yclients_list_services",
        type="function",
        description="Получить список услуг клиники",
        parameters={
            "type": "object",
            "properties": {
                "branch_id": {
                    "type": "integer",
                    "description": "ID филиала клиники (опционально, для совместимости)"
                },
                "category": {
                    "type": "string",
                    "description": "Категория услуг (опционально)",
                    "enum": ["маникюр", "педикюр", "парикмахерские услуги", "уходы для волос", "окрашивание", "косметология", "визаж", "все"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Максимальное количество услуг",
                    "default": 202,
                    "minimum": 1,
                    "maximum": 202
                }
            },
            "required": []
        }
    ),

    Tool(
        name="yclients_search_slots",
        type="function",
        description="Найти свободные слоты для записи на услугу",
        parameters={
            "type": "object",
            "properties": {
                "doctor_id": {
                    "type": "integer",
                    "description": "ID врача"
                },
                "date": {
                    "type": "string",
                    "format": "date",
                    "description": "Дата поиска в формате YYYY-MM-DD "
                }
            },
            "required": ["doctor_id", "date"]
        }
    ),

    Tool(
        name="yclients_create_appointment",
        type="function",
        description="Создать запись на прием",
        parameters={
            "type": "object",
            "properties": {
                "service_id": {
                    "type": "integer",
                    "description": "ID услуги"
                },
                "doctor_id": {
                    "type": "integer",
                    "description": "ID врача"
                },
                "datetime": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Дата и время записи в формате ISO8601"
                },
                "client_name": {
                    "type": "string",
                    "description": "Имя клиента",
                    "minLength": 2,
                    "maxLength": 100
                },
                "client_phone": {
                    "type": "string",
                    "description": "Телефон клиента в формате +7XXXXXXXXXX",
                    "pattern": "^\\+7\\d{10}$"
                },
                "comment": {
                    "type": "string",
                    "description": "Комментарий к записи (опционально)",
                    "maxLength": 500
                }
            },
            "required": ["service_id", "doctor_id", "datetime", "client_name", "client_phone"]
        }
    ),

    Tool(
        name="yclients_list_doctors",
        type="function",
        description="Получить список врачей клиники",
        parameters={
            "type": "object",
            "properties": {
                "specialization": {
                    "type": "string",
                    "description": "Специализация врача (опционально)",
                    "enum": ["терапевт", "хирург", "ортопед", "ортодонт", "имплантолог", "гигиенист"]
                }
            },
            "required": []
        }
    ),

    # Закомментированы инструменты работы с профилями
    # Tool(
    #     name="get_user_info",
    #     type="function",
    #     description="Получить информацию о пользователе: сначала из локального профиля, если нет - из Telegram. Если telegram_id не указан, используется ID текущего пользователя",
    #     parameters={
    #         "type": "object",
    #         "properties": {
    #             "telegram_id": {
    #                 "type": "integer",
    #                 "description": "ID пользователя в Telegram (опционально, по умолчанию текущий пользователь)"
    #             }
    #         },
    #         "required": []
    #     }
    # ),

    # Tool(
    #     name="register_user",
    #     type="function",
    #     description="Зарегистрировать нового пользователя в системе с созданием профиля в YClients",
    #     parameters={
    #         "type": "object",
    #         "properties": {
    #             "telegram_id": {
    #                 "type": "integer",
    #                 "description": "ID пользователя в Telegram"
    #             },
    #             "name": {
    #                 "type": "string",
    #                 "description": "Полное имя пользователя",
    #                 "minLength": 2,
    #                 "maxLength": 100
    #             },
    #             "phone": {
    #                 "type": "string",
    #                 "description": "Номер телефона в формате +7XXXXXXXXXX",
    #                 "pattern": "^\\+7\\d{10}$"
    #             }
    #         },
    #         "required": ["telegram_id", "name", "phone"]
    #     }
    # ),

    # Tool(
    #     name="book_appointment_with_profile",
    #     type="function",
    #     description="Записать пользователя на прием используя сохраненный профиль (не требует имя и телефон)",
    #     parameters={
    #         "type": "object",
    #         "properties": {
    #             "telegram_id": {
    #                 "type": "integer",
    #                 "description": "ID пользователя в Telegram"
    #             },
    #             "service": {
    #                 "type": "string",
    #                 "description": "Название услуги"
    #             },
    #             "doctor": {
    #                 "type": "string",
    #                 "description": "Имя врача"
    #             },
    #             "datetime": {
    #                 "type": "string",
    #                 "description": "Дата и время записи в формате YYYY-MM-DD HH:MM или YYYY-MM-DDTHH:MM"
    #             },
    #             "comment": {
    #                 "type": "string",
    #                 "description": "Комментарий к записи (опционально)",
    #                 "maxLength": 500
    #             }
    #         },
    #         "required": ["telegram_id", "service", "doctor", "datetime"]
    #     }
    # ),

    # Tool(
    #     name="sync_user_profile",
    #     type="function",
    #     description="Синхронизировать профиль пользователя с данными из YClients",
    #     parameters={
    #         "type": "object",
    #         "properties": {
    #             "telegram_id": {
    #                 "type": "integer",
    #                 "description": "ID пользователя в Telegram"
    #             },
    #             "phone": {
    #                 "type": "string",
    #                 "description": "Номер телефона для поиска в YClients (опционально)",
    #                 "pattern": "^\\+7\\d{10}$"
    #             }
    #         },
    #         "required": ["telegram_id"]
    #     }
    # ),

]

# System instructions for the AI assistant
SYSTEM_INSTRUCTIONS = """Ты — AI-ассистент салона красоты.
Твоя задача: помогать клиентам с записью на процедуры, предоставлять информацию об услугах и ценах. 

📋 ВАЖНЫЕ ПРАВИЛА
	1.	На приветствие ("Привет", "Добрый день") — сразу отвечай дружелюбно.
	2.	Для информации (цены, услуги, свободные слоты, запись) ВСЕГДА используй инструменты yclients_*.
	3.	Никогда не придумывай цены, расписание или другие факты.
	4.	Если инструмент недоступен или ошибка — честно сообщи клиенту.
	5.	Отвечай кратко, но структурированно (списки, буллеты).
	6.	Всегда предлагай конкретные действия: «Записаться», «Посмотреть цены», «Выбрать время».
	7.	При записи уточняй имя и телефон клиента.
	8.	Ответы ограничивай 1200–1700 символами.
	9.	НЕ проверяй профили автоматически - сразу помогай с запросом"
"""

# Tool name to function mapping
TOOL_FUNCTIONS = {
    "yclients_list_services": "list_services",
    "yclients_search_slots": "search_slots",
    "yclients_create_appointment": "create_appointment",
    "yclients_list_doctors": "list_doctors",
    # Закомментированы функции работы с профилями
    # "get_user_info": "get_user_info",
    # "register_user": "register_user",
    # "book_appointment_with_profile": "book_appointment_with_profile",
    # "sync_user_profile": "sync_user_profile",
}


def get_tools() -> List[Tool]:
    """Get all available tools."""
    return YCLIENTS_TOOLS


def get_system_instructions() -> str:
    """Get system instructions for the AI assistant."""
    # Создаем новый экземпляр Settings для получения актуальных переменных окружения
    from ..config.env import Settings
    settings = Settings()
    
    # Используем переменную окружения, если она задана, иначе дефолтный промпт
    if settings.SYSTEM_INSTRUCTIONS:
        return settings.SYSTEM_INSTRUCTIONS
    
    return SYSTEM_INSTRUCTIONS


def get_tool_function_name(tool_name: str) -> str:
    """Get function name for tool name."""
    return TOOL_FUNCTIONS.get(tool_name, tool_name)


def get_tools_for_openai() -> List[Dict[str, Any]]:
    """Get tools in OpenAI Realtime API format."""
    from typing import Dict, Any
    import logging

    logger = logging.getLogger(__name__)

    tools_dict = []
    for tool in YCLIENTS_TOOLS:
        tools_dict.append({
            "type": tool.type,
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters
        })

    logger.info(f"Loaded {len(tools_dict)} tools from tools.py: {[t['name'] for t in tools_dict]}")
    return tools_dict
