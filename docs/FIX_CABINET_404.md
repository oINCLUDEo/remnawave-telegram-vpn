# Исправление 404 на Cabinet endpoints (/api/auth/*)

## ❌ Проблема

```bash
curl http://localhost:8081/api/auth/login -X POST -H "Content-Type: application/json" -d "{\"email\":\"test@test.com\",\"password\":\"test\"}"
{"detail":"Not Found"}

curl http://localhost:8081/docs
{"detail":"Not Found"}
```

При этом `/health/unified` работает нормально.

## ✅ Причины и решения

### Причина 1: CABINET_ENABLED не читается из .env (Docker)

**Проблема**: При запуске через Docker Compose, изменения в `.env` требуют **пересборки** или **перезапуска** контейнера.

**Решение**: Полностью пересоздайте контейнер:

```bash
# Остановите и удалите контейнер
docker-compose -f docker-compose.local.yml down

# Пересоздайте и запустите
docker-compose -f docker-compose.local.yml up -d

# Проверьте логи
docker-compose -f docker-compose.local.yml logs -f bot
```

**Примечание**: `docker-compose restart` не всегда подхватывает изменения в `.env`!

---

### Причина 2: Неправильный формат значения в .env

**Проблема**: Значение `CABINET_ENABLED` должно быть точно `true` (lowercase, без кавычек).

**Неправильно** ❌:
```env
CABINET_ENABLED=True
CABINET_ENABLED="true"
CABINET_ENABLED=TRUE
CABINET_ENABLED=yes
CABINET_ENABLED=1
```

**Правильно** ✅:
```env
CABINET_ENABLED=true
```

**Проверка**: Откройте `.env` и убедитесь:
```bash
# Windows
type .env | findstr CABINET_ENABLED

# Linux/Mac
cat .env | grep CABINET_ENABLED
```

Должно быть **точно**:
```
CABINET_ENABLED=true
```

---

### Причина 3: WEB_API_ENABLED=false

**Проблема**: Если `WEB_API_ENABLED=false`, то Cabinet routes монтируются по-другому.

**Решение**: Убедитесь в `.env`:
```env
WEB_API_ENABLED=true
```

---

### Причина 4: Docs отключены

**Проблема**: `/docs` endpoint может быть отключен через `WEB_API_DOCS_ENABLED`.

**Решение**: Проверьте `.env`:
```env
# Должно быть true или не установлено (по умолчанию true)
WEB_API_DOCS_ENABLED=true
```

---

## 🔍 Диагностика

### Шаг 1: Проверьте что контейнер использует правильный .env

```bash
# Посмотрите переменные окружения в контейнере
docker exec remnawave_bot env | grep CABINET

# Должно вывести:
# CABINET_ENABLED=true
# CABINET_EMAIL_AUTH_ENABLED=true
# CABINET_ALLOWED_ORIGINS=*
```

Если вы НЕ видите `CABINET_ENABLED=true`, значит контейнер не читает .env правильно!

### Шаг 2: Проверьте логи запуска

```bash
docker-compose -f docker-compose.local.yml logs bot | grep -i cabinet
```

Должны быть логи о включении Cabinet.

### Шаг 3: Проверьте swagger

Если `/docs` недоступен, попробуйте:
```bash
curl http://localhost:8081/openapi.json
```

Если это тоже возвращает 404, значит docs полностью отключены.

### Шаг 4: Проверьте структуру .env файла

```bash
# Убедитесь что нет лишних пробелов
cat .env | grep "CABINET_ENABLED"

# Должно быть БЕЗ пробелов:
# CABINET_ENABLED=true
# НЕ: CABINET_ENABLED = true
```

---

## 🛠️ Полное решение (пошагово)

### 1. Проверьте .env файл

```bash
# Откройте .env в редакторе
notepad .env  # Windows
nano .env     # Linux/Mac
```

Убедитесь что есть **точно** эти строки (без пробелов вокруг =):
```env
CABINET_ENABLED=true
CABINET_EMAIL_AUTH_ENABLED=true
CABINET_ALLOWED_ORIGINS=*
WEB_API_ENABLED=true
WEB_API_PORT=8081
WEB_API_HOST=0.0.0.0
WEB_API_DOCS_ENABLED=true
```

### 2. Полностью пересоздайте контейнер

```bash
# Остановите все
docker-compose -f docker-compose.local.yml down

# ВАЖНО: Убедитесь что контейнер удален
docker ps -a | grep remnawave_bot

# Если все еще есть - удалите вручную
docker rm -f remnawave_bot

# Запустите заново
docker-compose -f docker-compose.local.yml up -d
```

### 3. Проверьте переменные в контейнере

```bash
docker exec remnawave_bot env | grep -E "CABINET|WEB_API"
```

Должно вывести:
```
CABINET_ENABLED=true
CABINET_EMAIL_AUTH_ENABLED=true
CABINET_ALLOWED_ORIGINS=*
WEB_API_ENABLED=true
WEB_API_PORT=8081
WEB_API_HOST=0.0.0.0
WEB_API_DOCS_ENABLED=true
```

### 4. Проверьте endpoints

```bash
# Health - должен работать
curl http://localhost:8081/health/unified

# Docs - должен работать
curl http://localhost:8081/docs

# OpenAPI schema - должен работать
curl http://localhost:8081/openapi.json

# Cabinet login - должен вернуть 400/401, НЕ 404
curl http://localhost:8081/api/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test"}'
```

---

## 🎯 Ожидаемое поведение

### ✅ Правильные ответы

**Health endpoint**:
```bash
curl http://localhost:8081/health/unified
# Возвращает JSON с информацией о системе
```

**Docs endpoint**:
```bash
curl http://localhost:8081/docs
# Возвращает HTML страницу Swagger UI
```

**Cabinet login (несуществующий пользователь)**:
```bash
curl http://localhost:8081/api/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test"}'

# Возвращает 400 или 401:
{"detail":"Invalid credentials"} # или подобное
```

### ❌ Неправильные ответы

Если вы видите `{"detail":"Not Found"}`, значит:
- Endpoint не зарегистрирован
- `CABINET_ENABLED` не активен
- Контейнер не прочитал `.env`

---

## 🔧 Альтернативное решение: Переменные в docker-compose

Если `.env` не работает, можно прописать переменные напрямую в `docker-compose.local.yml`:

```yaml
services:
  bot:
    # ... остальное ...
    environment:
      # ... существующие переменные ...
      CABINET_ENABLED: 'true'
      CABINET_EMAIL_AUTH_ENABLED: 'true'
      CABINET_ALLOWED_ORIGINS: '*'
      WEB_API_ENABLED: 'true'
      WEB_API_DOCS_ENABLED: 'true'
```

Затем:
```bash
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up -d
```

---

## 📋 Чек-лист

Перед обращением за помощью, проверьте:

- [ ] `.env` файл существует в той же директории что и `docker-compose.local.yml`
- [ ] `CABINET_ENABLED=true` в `.env` (точно так, lowercase, без пробелов)
- [ ] `WEB_API_ENABLED=true` в `.env`
- [ ] Контейнер полностью пересоздан (`docker-compose down` + `up`)
- [ ] `docker exec remnawave_bot env | grep CABINET_ENABLED` возвращает `CABINET_ENABLED=true`
- [ ] Логи не показывают ошибок: `docker-compose logs bot`
- [ ] `/health/unified` работает
- [ ] Порт 8081 открыт: `netstat -an | findstr :8081`

---

## 📚 Дополнительная информация

- [FLUTTER_CONNECTION.md](FLUTTER_CONNECTION.md) - Полная инструкция подключения Flutter
- [FIX_API_404.md](FIX_API_404.md) - Исправление 404 на других API endpoints
- [WINDOWS_SETUP.md](WINDOWS_SETUP.md) - Настройка на Windows
- [API_ONLY_MODE.md](API_ONLY_MODE.md) - Настройка API-only режима

---

## 💡 Совет

Если ничего не помогает, попробуйте запустить backend **без Docker**:

```bash
# Убедитесь что PostgreSQL и Redis запущены
docker-compose -f docker-compose.local.yml up -d postgres redis

# Остановите bot контейнер
docker-compose -f docker-compose.local.yml stop bot

# Запустите напрямую
python main.py
```

Так вы будете уверены что `.env` читается правильно.
