#!/bin/bash

# Скрипт для тестирования Docker образа локально

echo "🐳 Тестирование Docker образа для Railway..."

# Создаем .env файл для тестирования
if [ ! -f .env ]; then
    echo "📝 Создаем .env файл для тестирования..."
    cp railway.env.example .env
    echo "⚠️  Не забудьте заполнить реальные значения в .env файле!"
fi

# Собираем Docker образ
echo "🔨 Сборка Docker образа..."
docker build -t dental-bot-railway .

if [ $? -eq 0 ]; then
    echo "✅ Docker образ успешно собран!"
    
    # Запускаем контейнер
    echo "🚀 Запуск контейнера..."
    docker run --rm -p 8000:8000 --env-file .env dental-bot-railway
    
else
    echo "❌ Ошибка при сборке Docker образа!"
    exit 1
fi
