# 🤖 Telegram Bot Local Development Template

Готовый шаблон для локальной разработки Telegram-ботов с тремя вариантами реализации: 
- **python-telegram-bot v21+** (базовый)
- **aiogram v3** (базовый) 
- **aiogram v3 + OpenAI Realtime API** (продвинутый с AI и стримингом) 🆕

## 📋 Содержание

- [Особенности](#-особенности)
- [Требования](#-требования)
- [Быстрый старт](#-быстрый-старт)
- [Структура проекта](#-структура-проекта)
- [Варианты реализации](#-варианты-реализации)
- [Команды Makefile](#-команды-makefile)
- [Переменные окружения](#-переменные-окружения)
- [Разработка](#-разработка)
- [Линтинг и форматирование](#-линтинг-и-форматирование)
- [Полезные ссылки](#-полезные-ссылки)

## ✨ Особенности

- 🐍 **Python 3.11+** - современная версия Python
- 📦 **Poetry** - управление зависимостями и виртуальным окружением
- 🔄 **Long Polling** - без необходимости настройки вебхуков
- 🎯 **Два варианта** - python-telegram-bot и aiogram в одном репозитории
- 🛠️ **Makefile** - удобные команды для всех операций
- 🔍 **Линтинг** - ruff для проверки качества кода
- 📝 **Типизация** - mypy для статической проверки типов
- 🌍 **Переменные окружения** - безопасное хранение токенов
- 🧹 **Готовые хэндлеры** - базовый функционал из коробки

## 📋 Требования

- **Python 3.11+**
- **Poetry** ([инструкция по установке](https://python-poetry.org/docs/#installation))
- **Токен бота** от [@BotFather](https://t.me/BotFather)

### Установка Poetry (если не установлен)

```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

## 🚀 Быстрый старт

### 1. Клонирование и настройка

```bash
# Клонируем репозиторий
git clone <repository-url>
cd telegram-bot-local-dev

# Полная настройка проекта (установка зависимостей + копирование .env)
make setup
```

### 2. Настройка токена бота

```bash
# Отредактируйте файл .env и добавьте ваш токен
nano .env

# Или скопируйте токен напрямую:
echo "BOT_TOKEN=your_actual_bot_token_here" > .env
```

### 3. Запуск бота

**Вариант A: python-telegram-bot**
```bash
make run-ptb
```

**Вариант B: aiogram**
```bash
make run-aiogram
```

**Вариант C: aiogram + OpenAI Realtime API** 🆕
```bash
# Добавьте OPENAI_API_KEY в .env
echo "OPENAI_API_KEY=sk-your_key_here" >> .env

# Запустите продвинутую версию
make run-realtime
```

### 4. Тестирование

Отправьте боту сообщение `/start` в Telegram, и он ответит приветствием!

## 📁 Структура проекта

```
telegram-bot-local-dev/
├── 📄 README.md              # Этот файл (базовая документация)
├── 📄 README-REALTIME.md     # Подробная документация по Realtime API 🆕
├── 📄 .gitignore             # Исключения для Git
├── 📄 .env.sample            # Шаблон переменных окружения
├── 📄 .env                   # Ваши переменные окружения (создается автоматически)
├── 📄 pyproject.toml         # Конфигурация Poetry и инструментов
├── 📄 requirements.txt       # Зависимости для pip 🆕
├── 📄 Makefile               # Команды для управления проектом
├── 📁 ptb/                   # Python Telegram Bot реализация (базовая)
│   ├── 📄 __init__.py
│   └── 📄 main.py            # Основной файл бота (PTB)
├── 📁 aiogram/               # Aiogram реализация (базовая)
│   ├── 📄 __init__.py
│   └── 📄 bot.py             # Основной файл бота (aiogram)
└── 📁 src/                   # Продвинутая реализация с Realtime API 🆕
    ├── 📁 config/            # Конфигурация и переменные окружения
    ├── 📁 realtime/          # OpenAI Realtime API клиент
    ├── 📁 telegram/          # Telegram handlers с стримингом
    ├── 📁 integrations/      # YCLIENTS API и кэширование
    ├── 📁 utils/             # Утилиты (logger, throttler)
    └── 📄 app.py             # Главный файл приложения
```

## 🔧 Варианты реализации

### A) python-telegram-bot v21+

**Файл:** `ptb/main.py`

**Особенности:**
- ✅ Зрелая библиотека с богатой документацией
- ✅ Синхронный и асинхронный API
- ✅ Удобные фильтры и хэндлеры
- ✅ Отличная типизация из коробки

**Запуск:**
```bash
make run-ptb
```

### B) aiogram v3

**Файл:** `aiogram/bot.py`

**Особенности:**
- ✅ Современная асинхронная библиотека
- ✅ Быстрая и легковесная
- ✅ Удобная работа с роутерами
- ✅ Отличная производительность

**Запуск:**
```bash
make run-aiogram
```

### C) aiogram v3 + OpenAI Realtime API 🆕

**Файл:** `src/app.py`

**Особенности:**
- ✅ **Стриминг ответов** в реальном времени через WebSocket
- ✅ **Function calling** с инструментами YCLIENTS API
- ✅ **Умный ассистент** для стоматологической клиники
- ✅ **Автоматическая отмена** предыдущих запросов
- ✅ **Rate limiting** и кэширование
- ✅ **Webhook и polling** режимы

**Запуск:**
```bash
make run-realtime
```

**Подробная документация:** [README-REALTIME.md](README-REALTIME.md)

## 🛠️ Команды Makefile

### Основные команды

```bash
make help              # Показать все доступные команды
make setup             # Полная настройка проекта
make install           # Установить зависимости
make run-ptb           # Запустить python-telegram-bot бота
make run-aiogram       # Запустить aiogram бота
make run-realtime      # Запустить бота с Realtime API 🆕
```

### Разработка и проверки

```bash
make lint              # Проверить код линтерами
make format            # Отформатировать код
make type-check        # Проверить типы с mypy
make check-all         # Запустить все проверки
make lint-fix          # Исправить автоматически исправляемые ошибки
```

### Утилиты

```bash
make clean             # Очистить временные файлы
make show-env          # Показать переменные окружения (токен скрыт)
make poetry-shell      # Активировать Poetry shell
make deps-update       # Обновить зависимости
make deps-export       # Экспортировать в requirements.txt
```

### Быстрые команды для разработки

```bash
make dev-ptb           # Быстрый запуск PTB (с копированием .env)
make dev-aiogram       # Быстрый запуск aiogram (с копированием .env)
make dev-realtime      # Быстрый запуск Realtime API (с копированием .env) 🆕
make test-realtime     # Тестировать подключение к Realtime API 🆕
make webhook-mode      # Запустить в webhook режиме (продакшн) 🆕
```

## 🌍 Переменные окружения

Настройки в файле `.env`:

```bash
# Telegram Bot (обязательные)
TG_BOT_TOKEN=your_bot_token_here       # Токен от @BotFather
BOT_TOKEN=your_bot_token_here          # Для совместимости с базовыми ботами

# OpenAI Realtime API (для продвинутой версии) 🆕
OPENAI_API_KEY=sk-your_key_here        # OpenAI API ключ
REALTIME_MODEL=gpt-4o-realtime-preview # Модель Realtime API

# Опциональные настройки
LOG_LEVEL=INFO                         # Уровень логирования (DEBUG, INFO, WARNING, ERROR)
POLLING_TIMEOUT=10                     # Таймаут long polling (секунды)
REQUEST_TIMEOUT=30                     # Таймаут HTTP запросов (секунды)

# Продвинутые настройки (для Realtime API) 🆕
STREAM_THROTTLE_MS=300                 # Задержка между редактированиями сообщений
RATE_LIMIT_REQUESTS=5                  # Макс. запросов на пользователя
RATE_LIMIT_WINDOW=30                   # Окно rate limiting в секундах
TG_WEBHOOK_URL=https://your-domain.com # URL для webhook (продакшн)
```

### Получение токена бота

1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный токен в `.env`

## 👨‍💻 Разработка

### Добавление новых хэндлеров

**Python-telegram-bot:**
```python
async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Новая команда!")

# Регистрация
app.add_handler(CommandHandler("new", new_command))
```

**Aiogram:**
```python
@router.message(Command("new"))
async def new_command(message: Message) -> None:
    await message.answer("Новая команда!")
```

### Работа с базой данных

Добавьте в `pyproject.toml`:
```toml
[tool.poetry.dependencies]
sqlalchemy = "^2.0.0"    # Для работы с БД
aiosqlite = "^0.19.0"    # Для SQLite
```

### Добавление middleware (aiogram)

```python
from aiogram import BaseMiddleware

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Ваша логика
        return await handler(event, data)

# Регистрация
dp.message.middleware(LoggingMiddleware())
```

## 🔍 Линтинг и форматирование

Проект настроен с **ruff** (быстрый линтер и форматтер) и **mypy** (проверка типов).

### Конфигурация ruff

В `pyproject.toml` настроены:
- ✅ Длина строки: 88 символов
- ✅ Проверки: pycodestyle, pyflakes, isort, bugbear, comprehensions, pyupgrade
- ✅ Автоформатирование с двойными кавычками

### Команды для проверки кода

```bash
# Проверить весь код
make lint

# Исправить автоматически исправляемые ошибки
make lint-fix

# Отформатировать код
make format

# Проверить типы
make type-check

# Выполнить все проверки
make check-all
```

### Настройка IDE

**VS Code** (`.vscode/settings.json`):
```json
{
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "python.defaultInterpreterPath": ".venv/bin/python"
}
```

**PyCharm:**
- File → Settings → Tools → External Tools
- Добавьте ruff как external tool

## 🐛 Отладка

### Включение debug логирования

```bash
# В .env файле
LOG_LEVEL=DEBUG
```

### Проверка подключения к Telegram API

```python
# Добавьте в начало main функции
bot_info = await bot.get_me()
logger.info(f"Bot info: {bot_info}")
```

### Обработка ошибок

Оба варианта включают обработчики ошибок:
- Логирование в консоль
- Уведомление пользователя о проблеме
- Graceful shutdown при Ctrl+C

## 📚 Полезные ссылки

### Документация

- 📖 [python-telegram-bot docs](https://docs.python-telegram-bot.org/)
- 📖 [aiogram docs](https://docs.aiogram.dev/)
- 📖 [Telegram Bot API](https://core.telegram.org/bots/api)
- 📖 [Poetry docs](https://python-poetry.org/docs/)

### Инструменты

- 🔧 [Ruff](https://docs.astral.sh/ruff/) - линтер и форматтер
- 🔍 [MyPy](https://mypy.readthedocs.io/) - проверка типов
- 🤖 [@BotFather](https://t.me/BotFather) - создание ботов

### Примеры и туториалы

- 🎯 [PTB Examples](https://github.com/python-telegram-bot/python-telegram-bot/tree/master/examples)
- 🎯 [Aiogram Examples](https://github.com/aiogram/aiogram/tree/dev-3.x/examples)
- 📝 [Telegram Bot Tutorial](https://core.telegram.org/bots/tutorial)

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch: `git checkout -b feature/amazing-feature`
3. Commit изменения: `git commit -m 'Add amazing feature'`
4. Push в branch: `git push origin feature/amazing-feature`
5. Создайте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.

## ❓ FAQ

**Q: Какую библиотеку выбрать?**
A: 
- **Начинающим**: `python-telegram-bot` (простая)
- **Опытным разработчикам**: `aiogram` (быстрая)  
- **Для AI-проектов**: `aiogram + Realtime API` (продвинутая) 🆕

**Q: Можно ли использовать все варианты одновременно?**
A: Нет, запускайте только один бот за раз с одним токеном.

**Q: Нужен ли OpenAI API ключ для базовых версий?**
A: Нет, OpenAI API нужен только для продвинутой версии (`make run-realtime`).

**Q: Поддерживается ли стриминг в базовых версиях?**
A: Нет, стриминг ответов доступен только в версии с Realtime API.

**Q: Как деплоить в продакшн?**
A: Продвинутая версия поддерживает webhook режим. См. [README-REALTIME.md](README-REALTIME.md).

**Q: Поддерживаются ли вебхуки?**
A: Да, в продвинутой версии есть поддержка webhook для продакшна (`make webhook-mode`).

---

<div align="center">
  <strong>🚀 Удачной разработки Telegram-ботов! 🤖</strong>
</div>
