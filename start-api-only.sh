#!/bin/bash

# API-Only Mode Quick Start Script
# Помогает быстро запустить backend в режиме API-only

set -e

echo "🚀 API-Only Mode - Quick Start"
echo "================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Создаю .env файл из .env.api-only.example..."
    cp .env.api-only.example .env
    echo "✅ Файл .env создан"
    echo ""
    echo "⚠️  ВАЖНО: Отредактируйте .env и установите:"
    echo "   - CABINET_JWT_SECRET (сгенерируйте: openssl rand -hex 32)"
    echo "   - REMNAWAVE_API_URL"
    echo "   - REMNAWAVE_API_KEY"
    echo ""
    read -p "Нажмите Enter после настройки .env..." dummy
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose не установлен"
    exit 1
fi

echo "✅ Docker найден"
echo ""

# Check if services are already running
if docker ps | grep -q vpn-postgres || docker ps | grep -q vpn-api; then
    echo "⚠️  Сервисы уже запущены. Останавливаю..."
    docker-compose -f docker-compose.api-only.yml down
    echo ""
fi

# Start services
echo "🚀 Запускаю сервисы..."
echo ""
docker-compose -f docker-compose.api-only.yml up -d

echo ""
echo "⏳ Жду запуска сервисов..."
sleep 5

# Check if services are running
if docker ps | grep -q vpn-postgres && docker ps | grep -q vpn-redis && docker ps | grep -q vpn-api; then
    echo "✅ Все сервисы запущены успешно!"
    echo ""
    echo "📊 Статус сервисов:"
    docker-compose -f docker-compose.api-only.yml ps
    echo ""
    echo "🌐 API доступен на:"
    echo "   - Cabinet API: http://localhost:8000/cabinet"
    echo "   - Swagger UI:  http://localhost:8000/docs"
    echo "   - ReDoc:       http://localhost:8000/redoc"
    echo ""
    echo "📝 Логи API:"
    echo "   docker-compose -f docker-compose.api-only.yml logs -f api"
    echo ""
    echo "🛑 Остановить сервисы:"
    echo "   docker-compose -f docker-compose.api-only.yml down"
    echo ""
    echo "✅ Backend готов для Flutter разработки!"
    echo ""
    
    # Try to open Swagger in browser
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:8000/docs 2>/dev/null || true
    elif command -v open &> /dev/null; then
        open http://localhost:8000/docs 2>/dev/null || true
    fi
else
    echo "❌ Ошибка запуска сервисов"
    echo ""
    echo "Проверьте логи:"
    docker-compose -f docker-compose.api-only.yml logs
    exit 1
fi
