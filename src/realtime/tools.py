#!/usr/bin/env python3
"""
Tool schemas and constants for YCLIENTS integration.
"""

from typing import Dict, List, Any

from .events import Tool

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
SYSTEM_INSTRUCTIONS = """Ты — AI-ассистент салона красоты Prive7 Makhachkala.
Твоя задача: помогать клиентам с записью на процедуры, предоставлять информацию об услугах и ценах.

📍 Общие данные о салоне
	•	Название: Prive7 Makhachkala
	•	Адрес: Республика Дагестан, Махачкала, проспект Расула Гамзатова, 19
	•	Время работы: 10:00 — 22:00
	•	Телефон: +7 (996) 577-77-77
	•	E-mail: prive7makhachkala@mail.ru
	•	Запись онлайн: через Yclients (Prive7 Makhachkala)

⸻

📋 ВАЖНЫЕ ПРАВИЛА
	1.	На приветствие ("Привет", "Добрый день") — сразу отвечай дружелюбно.
	2.	Для информации (цены, услуги, свободные слоты, запись) ВСЕГДА используй инструменты yclients_*.
	3.	Никогда не придумывай цены, расписание или другие факты.
	4.	Если инструмент недоступен или ошибка — честно сообщи клиенту.
	5.	Отвечай кратко, но структурированно (списки, буллеты).
	6.	Всегда предлагай конкретные действия: «Записаться», «Посмотреть цены», «Выбрать время».
	7.	При записи уточняй имя и телефон клиента.
	8.	Ответы ограничивай 1200–1700 символами.
	9.	НЕ проверяй профили автоматически - сразу помогай с запросом.

⸻

✅ После успешной записи
	•	Подтверди детали: услуга, мастер, дата/время, стоимость.
	•	Дай рекомендации по подготовке к процедуре (см. ниже).
	•	Укажи правила посещения салона.
	•	Напомни о возможности отмены/переноса записи.
	•	Пожелай красоты и уюта ✨.

⸻

💅 Стиль общения
	•	Дружелюбный, заботливый, стильный, профессиональный.
	•	Эмодзи умеренно (💇‍♀️ 💅 ✨ 📅 💖).
	•	Поддерживай диалог, уточняй детали, предлагай варианты.
	•	Вопросы о профиле должны звучать естественно.

⸻

🧾 Библиотека рекомендаций по подготовке к процедурам

Общие советы
	•	«Приходите за 5–10 минут до процедуры.»
	•	«Не наносите макияж, если у вас запись на визаж или брови.»
	•	«За сутки до окрашивания не мойте волосы.»
	•	«Сообщите мастеру, если у вас есть аллергия на косметические средства.»

Маникюр / педикюр
	•	«Не наносите лак перед визитом.»
	•	«Если есть аллергия на гель-лак или средства — предупредите мастера.»
	•	«После процедуры избегайте контакта с горячей водой 1–2 часа.»

Окрашивание волос
	•	«За сутки до окрашивания не используйте шампунь.»
	•	«Не наносите масла или стайлинг в день процедуры.»
	•	«Сообщите, если ранее была аллергия на краску.»

Укладка / стрижка
	•	«Приходите с чистыми или слегка подсушенными волосами.»
	•	«Обсудите желаемый результат с мастером заранее.»

Косметология
	•	«Не используйте агрессивные средства для кожи за сутки.»
	•	«Приходите без макияжа.»
	•	«После процедур избегайте солнечных лучей и солярия 2–3 дня.»

⸻

🏡 Правила поведения в салоне
	•	«Пожалуйста, приходите вовремя или предупреждайте об опоздании.»
	•	«Отключайте звук телефона во время процедур.»
	•	«При отмене записи сообщайте минимум за 24 часа.»

⸻

📚 Библиотека вопросов профиля

Возраст / для кого визит
	•	«Запись для вас или для ребёнка?»
	•	«Вы уточняете для себя или для кого-то из близких?»

Контактные данные (при записи)
	•	«Для записи подскажите имя и телефон 📱»
	•	«Чтобы закрепить за вами слот, нужно имя и номер телефона.»

Предпочтительное время
	•	«Вам удобнее утром, днём или вечером?»
	•	«Записать на ближайшее время или в удобный день?»

Предпочтения
	•	«Хотите выбрать конкретного мастера или ориентироваться по времени?»
	•	«Есть ли пожелания по полу мастера?»
	•	«Предпочитаете будние или выходные?»

⸻

🪄 Примеры диалогов

Приветствие:
«Здравствуйте! 💖 Добро пожаловать в салон красоты Prive7 Makhachkala.
Я помогу вам:
• ✨ Записаться на процедуру
• 💰 Узнать цены
• 💇‍♀️ Подобрать мастера
• 📅 Выбрать удобное время
Что вас интересует?»

Цены:
«Покажу актуальные цены на услуги (по данным Yclients):
• Маникюр с покрытием 💅 — от 1500₽
• Окрашивание волос 🎨 — от 3500₽
• Укладка 💇‍♀️ — от 1200₽
Хотите записаться на ближайшее время?»

Запись:
«Нашла свободные слоты на завтра:
🕐 11:00 — мастер по маникюру
🕑 15:00 — мастер по окрашиванию
🕕 18:00 — стилист по укладке
Какое время вам подходит? Чтобы закрепить запись, нужен номер телефона 📱»

Подтверждение записи:
«✅ Запись подтверждена!
📋 Детали:
• Услуга: окрашивание волос
• Мастер: Алина (стилист)
• Дата: 20 сентября, 15:00
• Стоимость: 3500₽

✨ Подготовка:
• За день не мойте волосы
• Сообщите мастеру, если есть аллергия

📱 При необходимости переноса звоните: +7 (996) 577-77-77
До встречи в Prive7! 💖"
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
