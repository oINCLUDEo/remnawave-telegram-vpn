# API-Only Mode - Быстрый старт

## 🎯 Что это?

**API-Only Mode** - режим работы backend без Telegram бота, только с REST API для Flutter/мобильных приложений.

## ⚡ Быстрый запуск за 3 минуты

### Способ 1: Автоматический (рекомендуется)

```bash
# Запустите скрипт
./start-api-only.sh
```

Скрипт автоматически:
- Создаст `.env` из примера
- Запустит PostgreSQL, Redis и API
- Откроет Swagger UI в браузере

### Способ 2: Вручную

```bash
# 1. Создайте конфигурацию
cp .env.api-only.example .env

# 2. Отредактируйте .env (обязательно!)
nano .env
# Установите:
# - CABINET_JWT_SECRET (генерация: openssl rand -hex 32)
# - REMNAWAVE_API_URL
# - REMNAWAVE_API_KEY

# 3. Запустите сервисы
docker-compose -f docker-compose.api-only.yml up -d

# 4. Проверьте
open http://localhost:8000/docs
```

## 📍 После запуска

API доступен на:
- **Cabinet API:** http://localhost:8000/cabinet
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 🧪 Проверка работы

```bash
# Регистрация тестового пользователя
curl -X POST http://localhost:8000/cabinet/auth/register-email \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!",
    "first_name": "Test"
  }'

# Вход
curl -X POST http://localhost:8000/cabinet/auth/login-email \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!"
  }'
```

## 📱 Следующие шаги

1. **API работает** ✅
2. **Создайте Flutter приложение:** См. `docs/FLUTTER_QUICKSTART.md`
3. **Интегрируйте API:** См. `docs/FLUTTER_INTEGRATION.md`
4. **Изучите архитектуру:** См. `docs/FLUTTER_ARCHITECTURE.md`

## 📚 Полная документация

- **API-Only Mode Guide:** `docs/API_ONLY_MODE.md`
- **API Reference:** `docs/API_REFERENCE.md`
- **Flutter Integration:** `docs/FLUTTER_INTEGRATION.md`

## 🛑 Управление

```bash
# Просмотр логов
docker-compose -f docker-compose.api-only.yml logs -f api

# Остановка
docker-compose -f docker-compose.api-only.yml down

# Перезапуск
docker-compose -f docker-compose.api-only.yml restart api

# Статус
docker-compose -f docker-compose.api-only.yml ps
```

## 🐛 Проблемы?

См. раздел "Отладка" в `docs/API_ONLY_MODE.md`

---

**Готово к разработке! 🚀**
