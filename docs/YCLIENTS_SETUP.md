# Настройка YClients API

## Переменные окружения

Добавьте следующие переменные в ваш `.env` файл:

```bash
# YClients API настройки (из вашего curl запроса)
YCLIENTS_TOKEN=nmnsgmfcpdu65db2b5kp
YCLIENTS_COMPANY_ID=1488294
YCLIENTS_FORM_ID=0
YCLIENTS_LOGIN=your-yclients-login@example.com
YCLIENTS_PASSWORD=your-yclients-password
```

## Как получить необходимые данные

### 1. API Token
- ✅ **Из curl запроса**: `nmnsgmfcpdu65db2b5kp` (Bearer token)
- Это ваш Partner Token для доступа к API

### 2. Company ID  
- ✅ **Из curl запроса**: `1488294` (из URL `/staff/1488294`)
- Это ID вашей компании в YClients

### 3. Form ID
- ✅ **Можно оставить**: `0` (стандартное значение)
- Или найдите в настройках онлайн записи

### 4. Login/Password
- Ваши данные для входа в YClients
- Используются для получения User Token (расширенные права)

## Работа с YClients API

Бот работает **ТОЛЬКО** с реальным YClients API. Все переменные окружения обязательны:
- ✅ Получает реальные услуги из YClients
- ✅ Показывает актуальных врачей
- ✅ Ищет свободные слоты в реальном времени
- ✅ Создает записи в вашей системе

⚠️ **ВАЖНО**: Если настройки YClients неполные, бот не запустится!

## Проверка подключения

В логах бота вы увидите:
```
✅ YClients API инициализирован
✅ YClients user token получен
📋 Получено X услуг через YClients
👨‍⚕️ Получено X врачей через YClients
```

При ошибках (бот не запустится):
```
 YClients настройки обязательны! Добавьте YCLIENTS_TOKEN и YCLIENTS_COMPANY_ID в .env файл
 Ошибка инициализации YClients API: [детали]
```

## Установка библиотеки

```bash
pip install yclients-api
```

Библиотека уже добавлена в `requirements.txt`.

## Тестирование

### Проверка curl запроса (опционально)
Сначала можете проверить, что данные работают:
```bash
curl --location 'https://api.yclients.com/api/v1/staff/1488294' \
--header 'Accept: application/vnd.yclients.v2+json' \
--header 'Authorization: Bearer nmnsgmfcpdu65db2b5kp'
```

Должен вернуть список сотрудников в JSON формате.

### Тестирование бота
1. **Создайте файл `.env`** в корне проекта со следующим содержимым:
```bash
# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key-here

# Telegram Bot  
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here

# YClients API (рабочие данные)
YCLIENTS_TOKEN=nmnsgmfcpdu65db2b5kp
YCLIENTS_COMPANY_ID=1488294
YCLIENTS_FORM_ID=0
YCLIENTS_LOGIN=your-yclients-login@example.com
YCLIENTS_PASSWORD=your-yclients-password
```

2. Замените `OPENAI_API_KEY` и `TELEGRAM_BOT_TOKEN` на ваши реальные ключи
3. Перезапустите бота
4. Спросите у бота: "Покажи услуги" или "Кто из врачей работает?"
5. Проверьте логи на наличие сообщений от YClients API

## Дополнительная информация

- [YClients API документация](https://pypi.org/project/yclients-api/)
- [Официальный сайт YClients](https://yclients.com/)

## Поддержка

Если возникают проблемы с подключением:
1. Проверьте правильность всех токенов
2. Убедитесь, что у вашего аккаунта есть права API
3. Проверьте логи бота на ошибки
4. Исправьте настройки - бот не запустится без корректной конфигурации YClients
