# 🚀 Руководство по деплою на Railway

Этот документ содержит пошаговые инструкции для деплоя Telegram-бота стоматологической клиники на Railway.

## 📋 Предварительные требования

1. **Аккаунт Railway**: Зарегистрируйтесь на [railway.app](https://railway.app)
2. **GitHub репозиторий**: Убедитесь, что код находится в GitHub
3. **API ключи**:
   - Telegram Bot Token (от @BotFather)
   - OpenAI API Key
   - YClients API токены

## 🔧 Подготовка проекта

Проект уже подготовлен для деплоя со следующими файлами:

- `railway.json` - конфигурация Railway
- `Dockerfile` - для контейнеризации
- `Procfile` - команда запуска
- `railway.env.example` - пример переменных окружения

## 🚀 Пошаговый деплой

### 1. Создание проекта в Railway

1. Войдите в [Railway Dashboard](https://railway.app/dashboard)
2. Нажмите "New Project"
3. Выберите "Deploy from GitHub repo"
4. Выберите ваш репозиторий с ботом
5. Railway автоматически определит, что это Python проект

### 2. Настройка переменных окружения

В разделе "Variables" добавьте следующие переменные:

#### Обязательные переменные:
```bash
TG_BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
YCLIENTS_PARTNER_TOKEN=your_yclients_partner_token_here
YCLIENTS_USER_TOKEN=your_yclients_user_token_here
```

#### Дополнительные переменные (опционально):
```bash
TG_WEBHOOK_URL=https://your-app-name.railway.app
TG_WEBHOOK_PATH=/webhook
TG_WEBHOOK_PORT=8000
WS_POOL_SIZE=5
CACHE_TTL=3600
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### 3. Настройка домена

1. В разделе "Settings" → "Domains"
2. Railway автоматически создаст домен вида `your-app-name.railway.app`
3. Скопируйте этот URL и добавьте в переменную `TG_WEBHOOK_URL`

### 4. Настройка webhook

После деплоя настройте webhook для Telegram бота:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app-name.railway.app/webhook",
    "allowed_updates": ["message", "callback_query"]
  }'
```

## 🔍 Мониторинг и логи

### Просмотр логов
1. В Railway Dashboard перейдите в раздел "Deployments"
2. Выберите последний деплой
3. Перейдите на вкладку "Logs"

### Health Check
Бот предоставляет endpoint для проверки здоровья:
```
GET https://your-app-name.railway.app/health
```

Ответ:
```json
{
  "status": "healthy",
  "bot_info": {
    "id": 123456789,
    "username": "your_bot_username"
  }
}
```

## 🛠️ Устранение неполадок

### Частые проблемы:

1. **Ошибка "Module not found"**
   - Убедитесь, что все зависимости указаны в `requirements.txt`
   - Проверьте, что `PYTHONPATH` установлен в Dockerfile

2. **Webhook не работает**
   - Проверьте, что `TG_WEBHOOK_URL` указан правильно
   - Убедитесь, что домен доступен извне

3. **Ошибки подключения к API**
   - Проверьте правильность API ключей
   - Убедитесь, что все необходимые переменные окружения установлены

4. **Высокое потребление памяти**
   - Уменьшите `WS_POOL_SIZE` в переменных окружения
   - Настройте `CACHE_MAX_SIZE` для ограничения кеша

### Логи для отладки:

```bash
# Проверка статуса бота
curl https://your-app-name.railway.app/health

# Проверка webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

## 📊 Мониторинг производительности

Railway предоставляет метрики:
- CPU использование
- Память
- Сетевой трафик
- Время ответа

## 🔄 Обновления

Для обновления бота:
1. Сделайте изменения в коде
2. Запушьте в GitHub
3. Railway автоматически пересоберет и перезапустит приложение

## 💰 Стоимость

Railway предоставляет:
- Бесплатный план с ограничениями
- Платные планы для production использования

Проверьте актуальные тарифы на [railway.app/pricing](https://railway.app/pricing)

## 🔒 Безопасность

1. **Никогда не коммитьте** файлы с реальными API ключами
2. Используйте переменные окружения для всех секретов
3. Регулярно обновляйте зависимости
4. Мониторьте логи на предмет подозрительной активности

## 📞 Поддержка

- Railway Support: [railway.app/support](https://railway.app/support)
- Telegram Bot API: [core.telegram.org/bots/api](https://core.telegram.org/bots/api)
- OpenAI API: [platform.openai.com/docs](https://platform.openai.com/docs)

---

## ✅ Чек-лист деплоя

- [ ] Код загружен в GitHub
- [ ] Создан проект в Railway
- [ ] Настроены все переменные окружения
- [ ] Домен настроен и доступен
- [ ] Webhook настроен в Telegram
- [ ] Health check работает
- [ ] Логи показывают успешный запуск
- [ ] Бот отвечает на сообщения

**Готово! 🎉 Ваш бот успешно развернут на Railway.**
