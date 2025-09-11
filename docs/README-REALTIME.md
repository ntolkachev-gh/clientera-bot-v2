# 🤖 Telegram Bot with OpenAI Realtime API

Продвинутый Telegram-бот для стоматологической клиники с интеграцией **OpenAI Realtime API**, стримингом ответов в реальном времени и поддержкой tool-calls для работы с YCLIENTS API.

## 🚀 Возможности

### ⚡ OpenAI Realtime API
- **Стриминг ответов** в реальном времени через WebSocket
- **Function calling** с инструментами YCLIENTS
- **Прерывание активных запросов** при получении новых сообщений
- **Автоматическое переподключение** при сбоях сети

### 🏥 Интеграция с YCLIENTS
- 📋 **Запись на прием** к врачу
- 💰 **Получение цен** на услуги
- 👨‍⚕️ **Список врачей** и специализаций
- 📅 **Поиск свободных слотов**
- 🏥 **Информация о филиалах**

### 🛡️ Надежность и производительность
- **Rate limiting** для пользователей
- **Кэширование** справочной информации
- **Throttling** редактирования сообщений
- **Маскирование PII** в логах
- **Graceful shutdown** и обработка ошибок

## 📋 Требования

- **Python 3.11+**
- **OpenAI API ключ** с доступом к Realtime API
- **Telegram Bot Token** от [@BotFather](https://t.me/BotFather)
- **Poetry** для управления зависимостями

## 🔧 Установка и настройка

### 1. Клонирование и установка зависимостей

```bash
# Клонируем репозиторий
git clone <repository-url>
cd telegram-bot-local-dev

# Устанавливаем зависимости
make install

# Или через Poetry напрямую
poetry install
```

### 2. Настройка переменных окружения

```bash
# Копируем шаблон
make copy-env

# Редактируем .env файл
nano .env
```

**Обязательные переменные:**
```bash
# Telegram Bot
TG_BOT_TOKEN=your_bot_token_from_botfather

# OpenAI Realtime API
OPENAI_API_KEY=sk-your_openai_api_key_here
```

**Опциональные переменные:**
```bash
# Для продакшена (webhook режим)
TG_WEBHOOK_URL=https://your-domain.com/webhook
TG_WEBHOOK_PORT=8080

# Настройки производительности
STREAM_THROTTLE_MS=300          # Задержка между редактированиями сообщений
RATE_LIMIT_REQUESTS=5           # Макс. запросов на пользователя
RATE_LIMIT_WINDOW=30            # Окно rate limiting в секундах
MAX_RESPONSE_LENGTH=1500        # Макс. длина ответа

# Логирование
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR
DEBUG=false
```

### 3. Получение API ключей

#### OpenAI API Key
1. Зарегистрируйтесь на [OpenAI Platform](https://platform.openai.com/)
2. Перейдите в [API Keys](https://platform.openai.com/api-keys)
3. Создайте новый ключ
4. **Важно:** Убедитесь, что у вас есть доступ к Realtime API

#### Telegram Bot Token
1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный токен

## 🚀 Запуск

### Режим разработки (Long Polling)

```bash
# Быстрый запуск с проверками
make dev-realtime

# Или напрямую
make run-realtime
```

### Режим продакшена (Webhook)

```bash
# Установите URL вебхука
export TG_WEBHOOK_URL=https://your-domain.com/webhook

# Запустите в webhook режиме
make webhook-mode
```

### Тестирование подключения

```bash
# Проверить подключение к Realtime API
make test-realtime

# Проверить конфигурацию
make show-env
```

## 🏗️ Архитектура проекта

```
src/
├── config/
│   └── env.py              # Конфигурация и переменные окружения
├── realtime/
│   ├── client.py           # OpenAI Realtime WebSocket клиент
│   ├── events.py           # Модели событий Realtime API
│   └── tools.py            # Схемы инструментов YCLIENTS
├── telegram/
│   └── handlers.py         # Telegram handlers с стримингом
├── integrations/
│   ├── yclients_adapter.py # YCLIENTS API адаптер (моки)
│   └── cache.py            # TTL кэш для данных
├── utils/
│   ├── logger.py           # Структурированное логирование
│   └── throttler.py        # Throttling и rate limiting
└── app.py                  # Главный файл приложения
```

## 🔄 Как работает стриминг

1. **Пользователь отправляет сообщение**
2. **Бот показывает "Думаю..."** как заглушку
3. **WebSocket подключается** к OpenAI Realtime API
4. **Стриминг начинается:**
   - `response.text.delta` → постепенное обновление текста
   - Throttling редактирований (300ms между правками)
   - Function calls → вызовы YCLIENTS API
5. **Финализация:** `response.text.done` → окончательный текст

### Пример потока данных

```
Пользователь: "Хочу записаться к стоматологу"
    ↓
Бот: "🤔 Думаю..." 
    ↓
WebSocket → OpenAI Realtime API
    ↓ 
Delta: "Конечно! Помогу"
Delta: "Конечно! Помогу записаться"
Delta: "Конечно! Помогу записаться. Покажу"
Function Call: yclients_list_services(branch_id=1)
    ↓
Delta: "Конечно! Помогу записаться. Покажу доступные услуги:"
Delta: "• Консультация: 1500₽\n• Лечение кариеса: 3500₽"
    ↓
Done: Финальный текст с кнопками "📋 Записаться"
```

## 🛠️ Разработка

### Добавление новых инструментов

1. **Добавьте схему в `tools.py`:**
```python
Tool(
    type="function",
    function=FunctionSchema(
        name="yclients_new_function",
        description="Описание функции",
        parameters={...}
    )
)
```

2. **Реализуйте в `yclients_adapter.py`:**
```python
async def new_function(self, param1: int, param2: str) -> Dict[str, Any]:
    # Ваша логика
    return {"result": "data"}
```

3. **Добавьте маппинг в `client.py`:**
```python
function_mapping = {
    "yclients_new_function": self.yclients_adapter.new_function,
}
```

### Кастомизация системных инструкций

Отредактируйте `SYSTEM_INSTRUCTIONS` в `src/realtime/tools.py`:

```python
SYSTEM_INSTRUCTIONS = """
Ты — ассистент стоматологии. 
Добавьте свои инструкции здесь...
"""
```

### Настройка кэширования

Измените TTL в `src/integrations/cache.py`:

```python
self.services_cache = TTLCache(default_ttl_seconds=1800)  # 30 минут
```

## 📊 Мониторинг и логи

### Структурированные логи

```bash
# Включить debug логи
echo "LOG_LEVEL=DEBUG" >> .env

# Посмотреть логи в реальном времени
tail -f logs/app.log
```

### Метрики производительности

```python
# В коде доступны метрики кэша
cache_stats = get_yclients_cache().stats()
print(cache_stats)
```

### Маскирование PII

Логи автоматически маскируют:
- 📞 Телефоны: `+7123***45`
- 📧 Email: `user***@domain.com`  
- 🔑 Токены: `sk-abc123***masked***`
- 👤 Имена: `И*** П***`

## 🧪 Тестирование

### Локальное тестирование

```bash
# Запуск в режиме разработки
make dev-realtime

# Отправьте боту тестовые сообщения:
# "Покажи цены"
# "Запиши к врачу"
# "Свободные слоты на завтра"
```

### Тестирование function calls

```bash
# Проверить YCLIENTS адаптер
python -c "
import asyncio
from src.integrations.yclients_adapter import get_yclients_adapter

async def test():
    adapter = get_yclients_adapter()
    branches = await adapter.list_branches()
    print(f'Branches: {len(branches)}')

asyncio.run(test())
"
```

### Нагрузочное тестирование

```bash
# Симуляция множественных запросов
python scripts/load_test.py
```

##  Устранение неполадок

### Частые проблемы

**1. WebSocket connection failed**
```bash
# Проверьте API ключ
make test-realtime

# Проверьте сетевое подключение
curl -I https://api.openai.com/v1/realtime
```

**2. Rate limit exceeded**
```bash
# Увеличьте лимиты в .env
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60
```

**3. Function calls не работают**
```bash
# Проверьте логи на уровне DEBUG
LOG_LEVEL=DEBUG make run-realtime
```

**4. Медленные ответы**
```bash
# Уменьшите throttling
STREAM_THROTTLE_MS=200
```

### Логи и отладка

```bash
# Включить детальные логи
export LOG_LEVEL=DEBUG

# Проверить статус WebSocket
grep "WebSocket" logs/app.log

# Проверить function calls
grep "Function call" logs/app.log
```

## 📦 Деплой в продакшн

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY ../requirements.txt .
RUN pip install -r requirements.txt

COPY ../src src/
COPY ../.env .env

CMD ["python", "-m", "src.app"]
```

### Systemd Service

```ini
[Unit]
Description=Telegram Bot with Realtime API
After=network.target

[Service]
Type=simple
User=bot
WorkingDirectory=/opt/telegram-bot
Environment=PYTHONPATH=/opt/telegram-bot
ExecStart=/opt/telegram-bot/.venv/bin/python -m src.app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Nginx (для webhook)

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    location /webhook {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🔒 Безопасность

### Переменные окружения
- ✅ Никогда не коммитьте `.env` файлы
- ✅ Используйте разные токены для dev/prod
- ✅ Ротируйте API ключи регулярно

### Webhook безопасность
```python
# Проверка IP адресов Telegram
ALLOWED_IPS = ["149.154.160.0/20", "91.108.4.0/22"]
```

### Rate Limiting
```python
# Настройки по умолчанию
RATE_LIMIT_REQUESTS=5    # 5 запросов
RATE_LIMIT_WINDOW=30     # за 30 секунд
```

## 📈 Масштабирование

### Горизонтальное масштабирование
- Используйте Redis для кэша вместо in-memory
- Настройте load balancer для webhook
- Используйте отдельные инстансы для разных филиалов

### Оптимизация производительности
```python
# Увеличьте пулы соединений
WS_PING_INTERVAL=30
WS_PING_TIMEOUT=15

# Настройте кэш
CACHE_TTL_SERVICES=3600    # 1 час
CACHE_TTL_SLOTS=300        # 5 минут
```

## 🤝 Contributing

1. Fork репозитория
2. Создайте feature branch: `git checkout -b feature/amazing-feature`
3. Commit изменения: `git commit -m 'Add amazing feature'`
4. Push в branch: `git push origin feature/amazing-feature`
5. Создайте Pull Request

## 📄 Лицензия

MIT License - см. файл `LICENSE`

## ❓ FAQ

**Q: Поддерживается ли аудио?**
A: Пока только текст. Аудио модальность в планах (TODO в коде).

**Q: Можно ли использовать другие LLM?**
A: Код заточен под OpenAI Realtime API. Для других моделей нужна адаптация.

**Q: Как добавить новые инструменты?**
A: См. раздел "Разработка" → "Добавление новых инструментов".

**Q: Поддерживается ли группы/каналы?**
A: Только приватные чаты. Для групп нужна доработка handlers.

---

<div align="center">
  <strong>🦷 Создано для современной стоматологии с ❤️</strong><br>
  <i>Powered by OpenAI Realtime API + aiogram 3</i>
</div>
