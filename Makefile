.PHONY: help install install-dev setup lint format type-check run-ptb run-aiogram clean test

# Цвета для вывода
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
WHITE := \033[0;37m
RESET := \033[0m

# Python команды
PYTHON := python3
# Если Poetry доступен, используем его, иначе используем обычный Python
POETRY := $(shell command -v poetry 2> /dev/null)
ifdef POETRY
    POETRY_RUN := $(POETRY) run
else
    POETRY_RUN := $(PYTHON)
endif

help: ## Показать справку по командам
	@echo "$(CYAN)🤖 Telegram Bot Local Development$(RESET)"
	@echo "$(CYAN)====================================$(RESET)"
	@echo ""
	@echo "$(GREEN)Доступные команды:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-20s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(BLUE)Примеры использования:$(RESET)"
	@echo "  make setup           # Полная настройка проекта"
	@echo "  make run-ptb         # Запуск python-telegram-bot варианта"
	@echo "  make run-aiogram     # Запуск aiogram варианта"
	@echo "  make lint            # Проверка кода линтерами"

setup: install copy-env ## Полная настройка проекта (установка + копирование .env)
	@echo "$(GREEN)✅ Проект настроен! Не забудьте отредактировать .env файл$(RESET)"

install: ## Установить все зависимости через Poetry или pip
	@echo "$(BLUE)📦 Устанавливаем зависимости...$(RESET)"
ifdef POETRY
	@echo "$(BLUE)Используем Poetry...$(RESET)"
	$(POETRY) install
else
	@echo "$(BLUE)Poetry не найден, используем pip...$(RESET)"
	$(PYTHON) -m pip install -r requirements.txt
endif
	@echo "$(GREEN)✅ Зависимости установлены$(RESET)"

install-dev: ## Установить только dev зависимости
	@echo "$(BLUE)🔧 Устанавливаем dev зависимости...$(RESET)"
	$(POETRY) install --only=dev
	@echo "$(GREEN)✅ Dev зависимости установлены$(RESET)"

copy-env: ## Скопировать .env.sample в .env (если .env не существует)
	@if [ ! -f .env ]; then \
		echo "$(BLUE)📋 Копируем .env.sample в .env...$(RESET)"; \
		cp .env.sample .env; \
		echo "$(YELLOW)⚠️  Не забудьте отредактировать .env и добавить свой BOT_TOKEN!$(RESET)"; \
	else \
		echo "$(GREEN)✅ Файл .env уже существует$(RESET)"; \
	fi

lint: ## Запустить линтеры (ruff)
	@echo "$(BLUE)🔍 Запускаем линтеры...$(RESET)"
	$(POETRY_RUN) ruff check .
	@echo "$(GREEN)✅ Линтинг завершен$(RESET)"

format: ## Отформатировать код (ruff format)
	@echo "$(BLUE)🎨 Форматируем код...$(RESET)"
	$(POETRY_RUN) ruff format .
	@echo "$(GREEN)✅ Форматирование завершено$(RESET)"

format-check: ## Проверить форматирование без изменений
	@echo "$(BLUE)🔍 Проверяем форматирование...$(RESET)"
	$(POETRY_RUN) ruff format --check .
	@echo "$(GREEN)✅ Проверка форматирования завершена$(RESET)"

type-check: ## Проверить типы с mypy
	@echo "$(BLUE)🔍 Проверяем типы...$(RESET)"
	$(POETRY_RUN) mypy ptb/ aiogram/
	@echo "$(GREEN)✅ Проверка типов завершена$(RESET)"

lint-fix: ## Исправить автоматически исправляемые проблемы линтера
	@echo "$(BLUE)🔧 Исправляем проблемы линтера...$(RESET)"
	$(POETRY_RUN) ruff check --fix .
	@echo "$(GREEN)✅ Автоисправление завершено$(RESET)"

check-all: lint format-check type-check ## Запустить все проверки (линтинг, форматирование, типы)
	@echo "$(GREEN)✅ Все проверки завершены$(RESET)"

run-ptb: ## Запустить бота на python-telegram-bot
	@echo "$(PURPLE)🚀 Запускаем python-telegram-bot бота...$(RESET)"
	@if [ ! -f .env ]; then \
		echo "$(RED) Файл .env не найден! Запустите: make copy-env$(RESET)"; \
		exit 1; \
	fi
	$(POETRY_RUN) $(PYTHON) ptb/main.py

run-aiogram: ## Запустить бота на aiogram
	@echo "$(PURPLE)🚀 Запускаем aiogram бота...$(RESET)"
	@if [ ! -f .env ]; then \
		echo "$(RED) Файл .env не найден! Запустите: make copy-env$(RESET)"; \
		exit 1; \
	fi
	$(POETRY_RUN) $(PYTHON) aiogram/bot.py

run-realtime: ## Запустить бота с OpenAI Realtime API
	@echo "$(PURPLE)🚀 Запускаем бота с Realtime API...$(RESET)"
	@if [ ! -f .env ]; then \
		echo "$(RED) Файл .env не найден! Запустите: make copy-env$(RESET)"; \
		exit 1; \
	fi
	@if ! grep -q "OPENAI_API_KEY=sk-" .env; then \
		echo "$(RED) OPENAI_API_KEY не настроен в .env$(RESET)"; \
		echo "$(YELLOW)Добавьте: OPENAI_API_KEY=sk-your_key_here$(RESET)"; \
		exit 1; \
	fi
	@if ! grep -q "TG_BOT_TOKEN=" .env; then \
		echo "$(RED) TG_BOT_TOKEN не настроен в .env$(RESET)"; \
		echo "$(YELLOW)Добавьте: TG_BOT_TOKEN=your_bot_token$(RESET)"; \
		exit 1; \
	fi
	$(POETRY_RUN) $(PYTHON) -m src.app

run-dental: ## Запустить стоматологический бота с Realtime API
	@echo "$(PURPLE)🦷 Запускаем стоматологического бота...$(RESET)"
	@if [ ! -f .env ]; then \
		echo "$(RED) Файл .env не найден! Запустите: make copy-env$(RESET)"; \
		exit 1; \
	fi
	$(POETRY_RUN) dental_bot.py

stop-bot: ## Остановить запущенный бот
	@echo "$(RED)🛑 Останавливаем бота...$(RESET)"
	$(POETRY_RUN) stop_bot.py

admin: ## Открыть админ-панель в браузере (бот должен быть запущен)
	@echo "$(BLUE)🌐 Открываем админ-панель...$(RESET)"
	@open http://localhost:8080 || echo "Откройте http://localhost:8080 в браузере"

test-admin: ## Тестировать админ API
	@echo "$(BLUE)🧪 Тестируем админ API...$(RESET)"
	$(POETRY_RUN) test_admin_api.py

dev-ptb: copy-env run-ptb ## Быстрый запуск python-telegram-bot (с копированием .env)

dev-aiogram: copy-env run-aiogram ## Быстрый запуск aiogram (с копированием .env)

dev-realtime: copy-env run-realtime ## Быстрый запуск Realtime API бота (с копированием .env)

webhook-mode: ## Запустить бота в webhook режиме (для продакшена)
	@echo "$(PURPLE)🌐 Запускаем бота в webhook режиме...$(RESET)"
	@if [ -z "$$TG_WEBHOOK_URL" ]; then \
		echo "$(RED) TG_WEBHOOK_URL не установлен$(RESET)"; \
		echo "$(YELLOW)Установите: export TG_WEBHOOK_URL=https://your-domain.com/webhook$(RESET)"; \
		exit 1; \
	fi
	TG_WEBHOOK_URL=$$TG_WEBHOOK_URL $(POETRY_RUN) $(PYTHON) -m src.app

test-realtime: ## Тестировать подключение к Realtime API
	@echo "$(BLUE)🔍 Тестируем подключение к OpenAI Realtime API...$(RESET)"
	@if ! grep -q "OPENAI_API_KEY=sk-" .env; then \
		echo "$(RED) OPENAI_API_KEY не настроен$(RESET)"; \
		exit 1; \
	fi
	$(POETRY_RUN) $(PYTHON) test_realtime.py

test-reconnection: ## Тестировать переподключение WebSocket
	@echo "$(BLUE)🔄 Тестируем переподключение WebSocket...$(RESET)"
	@if ! grep -q "OPENAI_API_KEY=sk-" .env; then \
		echo "$(RED) OPENAI_API_KEY не настроен$(RESET)"; \
		exit 1; \
	fi
	$(POETRY_RUN) $(PYTHON) test_reconnection.py

test-pool: ## Тестировать пул соединений с несколькими пользователями
	@echo "$(BLUE)🏊 Тестируем пул соединений...$(RESET)"
	@if ! grep -q "OPENAI_API_KEY=sk-" .env; then \
		echo "$(RED) OPENAI_API_KEY не настроен$(RESET)"; \
		exit 1; \
	fi
	$(POETRY_RUN) $(PYTHON) test_pool.py

test-doctors: ## Тестировать получение врачей из YClients API
	@echo "$(BLUE)👨‍⚕️ Тестируем получение врачей из YClients...$(RESET)"
	@if ! grep -q "YCLIENTS_TOKEN=" .env; then \
		echo "$(RED) YCLIENTS_TOKEN не настроен$(RESET)"; \
		exit 1; \
	fi
	@if ! grep -q "YCLIENTS_COMPANY_ID=" .env; then \
		echo "$(RED) YCLIENTS_COMPANY_ID не настроен$(RESET)"; \
		exit 1; \
	fi
	$(POETRY_RUN) test_doctors_api.py

test-auth: ## Тестировать формирование заголовка Authorization
	@echo "$(BLUE)🔐 Тестируем заголовок Authorization...$(RESET)"
	$(POETRY_RUN) test_auth_header.py

test-cache: ## Тестировать кеширование врачей
	@echo "$(BLUE)💾 Тестируем кеширование врачей...$(RESET)"
	@if ! grep -q "YCLIENTS_TOKEN=" .env; then \
		echo "$(RED) YCLIENTS_TOKEN не настроен$(RESET)"; \
		exit 1; \
	fi
	@if ! grep -q "YCLIENTS_COMPANY_ID=" .env; then \
		echo "$(RED) YCLIENTS_COMPANY_ID не настроен$(RESET)"; \
		exit 1; \
	fi
	$(POETRY_RUN) test_doctors_cache.py

test-services-cache: ## Тестировать кеширование услуг
	@echo "$(BLUE)💰 Тестируем кеширование услуг...$(RESET)"
	@if ! grep -q "YCLIENTS_TOKEN=" .env; then \
		echo "$(RED) YCLIENTS_TOKEN не настроен$(RESET)"; \
		exit 1; \
	fi
	@if ! grep -q "YCLIENTS_COMPANY_ID=" .env; then \
		echo "$(RED) YCLIENTS_COMPANY_ID не настроен$(RESET)"; \
		exit 1; \
	fi
	$(POETRY_RUN) test_services_cache.py

test-all-cache: ## Тестировать все кеши (врачи + услуги)
	@echo "$(BLUE)🔄 Тестируем все кеши...$(RESET)"
	@make test-cache
	@echo ""
	@make test-services-cache

test-yclients-adapter: ## Тестировать YClients адаптер для Realtime API
	@echo "$(BLUE)🔌 Тестируем YClients адаптер...$(RESET)"
	@if ! grep -q "YCLIENTS_TOKEN=" .env; then \
		echo "$(RED) YCLIENTS_TOKEN не настроен$(RESET)"; \
		exit 1; \
	fi
	@if ! grep -q "YCLIENTS_USER_TOKEN=" .env; then \
		echo "$(RED) YCLIENTS_USER_TOKEN не настроен$(RESET)"; \
		exit 1; \
	fi
	@if ! grep -q "YCLIENTS_COMPANY_ID=" .env; then \
		echo "$(RED) YCLIENTS_COMPANY_ID не настроен$(RESET)"; \
		exit 1; \
	fi
	$(POETRY_RUN) test_yclients_adapter.py

test-booking: ## Тестировать создание записи в YClients
	@echo "$(BLUE)📝 Тестируем создание записи в YClients...$(RESET)"
	@echo "$(YELLOW)⚠️  Внимание: создает реальную запись в системе!$(RESET)"
	@if ! grep -q "YCLIENTS_TOKEN=" .env; then \
		echo "$(RED) YCLIENTS_TOKEN не настроен$(RESET)"; \
		exit 1; \
	fi
	@if ! grep -q "YCLIENTS_USER_TOKEN=" .env; then \
		echo "$(RED) YCLIENTS_USER_TOKEN не настроен$(RESET)"; \
		exit 1; \
	fi
	@if ! grep -q "YCLIENTS_COMPANY_ID=" .env; then \
		echo "$(RED) YCLIENTS_COMPANY_ID не настроен$(RESET)"; \
		exit 1; \
	fi
	@echo "from dental_bot import YClientsIntegration; import asyncio; result = asyncio.run(YClientsIntegration().book_appointment('Тест Тестов', '+79999999999', 'консультация', 'Магомед Расулов', '2025-09-13T16:00', 'Тестовая запись')); print(f'Результат: {result}')" | python3

test-tls-fix: ## Тестировать исправление TLS ошибок (бот должен быть запущен)
	@echo "$(BLUE)🔒 Тестируем обработку TLS ошибок...$(RESET)"
	@echo "$(YELLOW)💡 Убедитесь, что бот запущен (AdminServer на порту 8080)$(RESET)"
	$(POETRY_RUN) test_tls_fix.py

clean: ## Очистить временные файлы и кэши
	@echo "$(BLUE)🧹 Очищаем временные файлы...$(RESET)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✅ Очистка завершена$(RESET)"

show-env: ## Показать текущие переменные окружения бота
	@echo "$(BLUE)🔍 Переменные окружения:$(RESET)"
	@if [ -f .env ]; then \
		echo "$(GREEN).env файл найден:$(RESET)"; \
		grep -v "^#" .env | grep -v "^$$" | while read line; do \
			key=$$(echo "$$line" | cut -d'=' -f1); \
			if [ "$$key" = "BOT_TOKEN" ]; then \
				echo "  $$key=***скрыто***"; \
			else \
				echo "  $$line"; \
			fi; \
		done; \
	else \
		echo "$(RED) .env файл не найден$(RESET)"; \
	fi

poetry-shell: ## Активировать Poetry shell
	@echo "$(BLUE)🐚 Активируем Poetry shell...$(RESET)"
	$(POETRY) shell

poetry-info: ## Показать информацию о Poetry проекте
	@echo "$(BLUE)📋 Информация о проекте:$(RESET)"
	$(POETRY) show --tree

deps-update: ## Обновить зависимости
	@echo "$(BLUE)📦 Обновляем зависимости...$(RESET)"
	$(POETRY) update
	@echo "$(GREEN)✅ Зависимости обновлены$(RESET)"

deps-export: ## Экспортировать зависимости в requirements.txt
	@echo "$(BLUE)📋 Экспортируем зависимости...$(RESET)"
	$(POETRY) export -f requirements.txt --output requirements.txt --without-hashes
	$(POETRY) export -f requirements.txt --output requirements-dev.txt --with=dev --without-hashes
	@echo "$(GREEN)✅ Зависимости экспортированы в requirements.txt и requirements-dev.txt$(RESET)"

# Алиасы для удобства
install-deps: install ## Алиас для install
run-python-telegram-bot: run-ptb ## Алиас для run-ptb
check: check-all ## Алиас для check-all
