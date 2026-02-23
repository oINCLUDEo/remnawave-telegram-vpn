# Исправление ошибки 404 на API endpoints

## ❌ Ошибка

```bash
curl http://localhost:8081/api/health
{"detail":"Not Found"}
```

## ✅ Решение

### Проблема 1: Неправильный endpoint для проверки

**Причина**: Endpoint `/api/health` требует API токен аутентификацию.

**Решение**: Используйте unified health endpoint:

```bash
# Правильный endpoint для проверки (без токена)
curl http://localhost:8081/health/unified
```

Этот endpoint возвращает информацию о состоянии системы без требования аутентификации.

---

### Проблема 2: Cabinet endpoints недоступны (404 на /api/auth/*)

**Причина**: `CABINET_ENABLED=false` в `.env`

**Решение**: Включите Cabinet в `.env`:

```env
# В файле .env
CABINET_ENABLED=true
CABINET_EMAIL_AUTH_ENABLED=true
```

**Перезапустите backend**:
```bash
# Если через Python
python main.py

# Если через Docker
docker-compose -f docker-compose.local.yml restart bot
```

**Проверка**:
```bash
curl http://localhost:8081/api/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test"}'

# Должен вернуть 400 или 401 (пользователь не существует)
# НЕ должен вернуть 404
```

---

### Проблема 3: Web API не запущен

**Причина**: `WEB_API_ENABLED=false` в `.env`

**Решение**: Включите Web API:

```env
# В файле .env
WEB_API_ENABLED=true
WEB_API_HOST=0.0.0.0
WEB_API_PORT=8081
```

**Перезапустите backend**.

---

## 🔍 Диагностика

### Шаг 1: Проверьте что backend запущен

```bash
# Для Docker
docker ps | findstr bot

# Для Python - должен быть запущен python main.py
```

### Шаг 2: Проверьте порт 8081

```bash
netstat -an | findstr :8081

# Должна быть строка с LISTENING
```

### Шаг 3: Проверьте конфигурацию .env

```bash
type .env | findstr "WEB_API_ENABLED\|CABINET_ENABLED"

# Должно быть:
# WEB_API_ENABLED=true
# CABINET_ENABLED=true
```

### Шаг 4: Проверьте unified health endpoint

```bash
curl http://localhost:8081/health/unified

# Должен вернуть JSON с информацией
```

Если этот endpoint работает, значит backend запущен правильно.

---

## 📋 Доступные endpoints

### Публичные endpoints (без токена)

```bash
# Unified health check
GET http://localhost:8081/health/unified

# Swagger документация (если WEB_API_DOCS_ENABLED=true)
GET http://localhost:8081/docs

# ReDoc документация
GET http://localhost:8081/redoc
```

### Cabinet endpoints (требуют CABINET_ENABLED=true)

```bash
# Вход
POST http://localhost:8081/api/auth/login
Content-Type: application/json
{"email": "user@example.com", "password": "password"}

# Регистрация
POST http://localhost:8081/api/auth/register
Content-Type: application/json
{"email": "user@example.com", "password": "password", "first_name": "User"}

# Обновление токена
POST http://localhost:8081/api/auth/refresh
Authorization: Bearer {refresh_token}

# Информация о пользователе
GET http://localhost:8081/api/users/me
Authorization: Bearer {access_token}

# Подписка пользователя
GET http://localhost:8081/api/users/me/subscription
Authorization: Bearer {access_token}
```

### Admin API endpoints (требуют API токен)

```bash
# Health check с токеном
GET http://localhost:8081/api/health
Authorization: Bearer {admin_token}

# Database health
GET http://localhost:8081/api/health/database
Authorization: Bearer {admin_token}

# Все остальные /api/* endpoints требуют admin токен
```

---

## 🔐 API токен для Admin API

Если вам нужен доступ к `/api/health` и другим admin endpoints:

### Шаг 1: Найдите токен в .env

```bash
type .env | findstr WEB_API_DEFAULT_TOKEN
```

### Шаг 2: Используйте токен в запросе

```bash
# Замените YOUR_TOKEN на значение из .env
curl http://localhost:8081/api/health \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## ⚠️ Частые ошибки

### Ошибка: "404 на /api/health"

**Решение**: Используйте `/health/unified` или добавьте токен:
```bash
curl http://localhost:8081/health/unified  # Без токена
# ИЛИ
curl http://localhost:8081/api/health -H "Authorization: Bearer YOUR_TOKEN"  # С токеном
```

### Ошибка: "404 на /api/auth/login"

**Решение**: Включите Cabinet:
```env
CABINET_ENABLED=true
CABINET_EMAIL_AUTH_ENABLED=true
```

### Ошибка: "Connection refused"

**Решение**: Backend не запущен или порт неправильный.

См. [FLUTTER_CONNECTION.md](FLUTTER_CONNECTION.md) для детальной диагностики.

---

## 📚 Дополнительная информация

- [FLUTTER_CONNECTION.md](FLUTTER_CONNECTION.md) - Подключение Flutter приложения
- [API_ONLY_MODE.md](API_ONLY_MODE.md) - Настройка API-only режима
- [WINDOWS_SETUP.md](WINDOWS_SETUP.md) - Настройка на Windows

---

## 🎯 Итоговый чек-лист

Для работы с API убедитесь:

- [ ] Backend запущен
- [ ] `WEB_API_ENABLED=true` в `.env`
- [ ] `WEB_API_PORT=8081` в `.env`
- [ ] `WEB_API_HOST=0.0.0.0` в `.env`
- [ ] Порт 8081 открыт и слушается
- [ ] `/health/unified` отвечает
- [ ] Для Flutter: `CABINET_ENABLED=true`
- [ ] Для Flutter: `CABINET_EMAIL_AUTH_ENABLED=true`
- [ ] Для admin API: есть `WEB_API_DEFAULT_TOKEN`
