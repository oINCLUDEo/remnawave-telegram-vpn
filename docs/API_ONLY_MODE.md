# API-Only Mode Configuration Guide

Этот гайд объясняет, как запустить backend в режиме API-only (без Telegram бота) для работы с Flutter приложением.

## Что изменилось

1. **Новая настройка**: `TELEGRAM_BOT_ENABLED` - контролирует запуск Telegram бота
2. **BOT_TOKEN теперь опциональный** - если `TELEGRAM_BOT_ENABLED=false`, токен не требуется
3. **Модифицирован main.py** - пропускает инициализацию бота и связанных сервисов при отключенном боте

## Быстрый старт

### 1. Настройка .env файла

Создайте `.env` файл на основе `.env.example`:

```bash
cp .env.example .env
```

### 2. Конфигурация для API-only режима

Отредактируйте `.env` и установите следующие параметры:

```env
# Отключаем Telegram бота
TELEGRAM_BOT_ENABLED=false

# BOT_TOKEN можно оставить пустым или закомментировать
# BOT_TOKEN=

# Включаем Web API
WEB_API_ENABLED=true
WEB_API_HOST=0.0.0.0
WEB_API_PORT=8081  # Измените если порт 8080 занят

# Настройки базы данных
DATABASE_MODE=postgres
# Для локального запуска на Windows/Mac/Linux используйте localhost
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=remnawave_bot
POSTGRES_USER=remnawave_user
POSTGRES_PASSWORD=your_secure_password

# Redis (для кеша и сессий)
# Для локального запуска используйте localhost
REDIS_URL=redis://localhost:6379/0

# RemnaWave API настройки
REMNAWAVE_API_URL=http://your-remnawave-server:port
REMNAWAVE_API_KEY=your_api_key
REMNAWAVE_SECRET_KEY=your_secret_key

# Email настройки (для регистрации через Cabinet)
# ВАЖНО: Для работы Flutter приложения включите Cabinet
CABINET_ENABLED=true
CABINET_EMAIL_AUTH_ENABLED=true
CABINET_EMAIL_VERIFICATION_ENABLED=false  # Для тестирования
CABINET_ALLOWED_ORIGINS=*  # Для разработки, в production укажите конкретные домены

# SMTP (если нужна отправка email)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_USE_TLS=true
```

**Важно для Windows пользователей:**
- Используйте `POSTGRES_HOST=localhost` вместо `postgres` (который работает только в Docker)
- Используйте `REDIS_URL=redis://localhost:6379/0` вместо `redis://redis:6379/0`
- Если порт 8080 занят, измените `WEB_API_PORT` на другой (например, 8081)

### 3. Запуск с Docker Compose

Самый простой способ:

```bash
docker-compose -f docker-compose.local.yml up -d
```

Или для production:

```bash
docker-compose up -d
```

### 4. Запуск без Docker (локальная разработка)

#### Установка зависимостей

```bash
pip install -r requirements.txt
```

#### Запуск PostgreSQL и Redis

```bash
# PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=your_secure_password \
  -e POSTGRES_DB=remnawave_bot \
  -e POSTGRES_USER=remnawave_user \
  -p 5432:5432 \
  postgres:15

# Redis
docker run -d --name redis \
  -p 6379:6379 \
  redis:7-alpine
```

#### Запуск миграций

```bash
python -m alembic upgrade head
```

#### Запуск приложения

```bash
python main.py
```

## API Endpoints для Flutter приложения

Backend предоставляет следующие эндпоинты для мобильного приложения:

### Authentication

```
POST /cabinet/auth/email/register/standalone
POST /cabinet/auth/email/login
POST /api/auth/refresh
```

### Users

```
GET /cabinet/auth/me
PUT /cabinet/auth/me
GET /cabinet/auth/me/subscription
```

### Subscriptions

```
GET /api/subscriptions
POST /api/subscriptions
PUT /api/subscriptions/{id}
```

### Servers

```
GET /api/servers
GET /api/servers/{id}
```

## Проверка работы

После запуска проверьте:

1. **Unified health endpoint** (без токена): 
   ```bash
   curl http://localhost:8081/health/unified
   ```
   
   Должен вернуть JSON с информацией о системе.
   
   **Примечание**: Endpoint `/api/health` требует API токен аутентификацию.

2. **Swagger документация** (если включена):
   ```
   http://localhost:8081/docs
   ```

3. **Логи запуска**:
   - Должно быть сообщение `TELEGRAM_BOT_ENABLED=false (API-only режим)`
   - Должно быть сообщение `🌐 Запуск административного API`

4. **Cabinet auth endpoints**:
   ```bash
   curl http://localhost:8081/cabinet/auth/email/login -X POST \
     -H "Content-Type: application/json" \
     -d '{"email":"test@test.com","password":"test"}'
   
   # Должен вернуть 400/401, НЕ 404
   ```

## Настройка Flutter приложения

### 1. Переход в директорию приложения

```bash
cd flutter_app/ulya_vpn
```

### 2. Установка зависимостей

```bash
flutter pub get
```

### 3. Настройка API URL

Отредактируйте `lib/config/api_config.dart`:

```dart
static const String baseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8081',  // Измените на ваш URL
);
```

Или используйте переменную окружения при запуске:

```bash
flutter run --dart-define=API_BASE_URL=http://192.168.1.100:8081
```

### 4. Запуск приложения

```bash
# Android emulator
flutter run

# iOS simulator
flutter run -d ios

# Конкретное устройство
flutter run -d <device_id>
```

## Тестирование

### Регистрация нового пользователя

```bash
curl -X POST http://localhost:8080/cabinet/auth/email/register/standalone \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### Вход

```bash
curl -X POST http://localhost:8080/cabinet/auth/email/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

Ответ содержит `access_token` и `refresh_token`.

### Получение данных пользователя

```bash
curl http://localhost:8081/cabinet/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Troubleshooting

### Проблема: "password authentication failed"

**Решение**: Пароль в `.env` не совпадает с PostgreSQL.

**Быстрое исправление**:
```bash
# Пересоздайте PostgreSQL контейнер
docker stop remnawave_postgres && docker rm remnawave_postgres
docker run -d --name remnawave_postgres \
  -e POSTGRES_PASSWORD=secure_password_123 \
  -e POSTGRES_DB=remnawave_bot \
  -e POSTGRES_USER=remnawave_user \
  -p 5432:5432 postgres:15
```

**Подробная инструкция**: См. [FIX_PASSWORD_ERROR.md](FIX_PASSWORD_ERROR.md)

---

### Проблема: "Missing API key"

**Решение**: Убедитесь, что вы передаете токен в заголовке:
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Проблема: База данных не инициализирована

**Решение**: Запустите миграции:
```bash
python -m alembic upgrade head
```

### Проблема: Connection refused при подключении из Flutter

**Решение**: 
1. Если тестируете на физическом устройстве, используйте IP вашего компьютера вместо `localhost`
2. Убедитесь, что `WEB_API_HOST=0.0.0.0` (не `127.0.0.1`)
3. Проверьте firewall настройки
4. **Для Android эмулятора используйте `10.0.2.2` вместо `localhost`**
5. **Убедитесь что `CABINET_ENABLED=true` в `.env`**

**Подробная инструкция**: См. [FLUTTER_CONNECTION.md](FLUTTER_CONNECTION.md)

---

### Проблема: CORS errors в браузере или Flutter

**Решение**: Настройте CORS в `.env`:
```env
WEB_API_ALLOWED_ORIGINS=http://localhost:3000,http://192.168.1.100:3000
```

## Production Deployment

### 1. Безопасность

- Используйте HTTPS (nginx/traefik reverse proxy)
- Настройте strong passwords для БД
- Включите rate limiting
- Используйте JWT секреты с высокой энтропией

### 2. Масштабирование

- Используйте PostgreSQL для production
- Настройте Redis cluster для высокой доступности
- Рассмотрите использование CDN для статических файлов

### 3. Мониторинг

- Настройте логирование в файлы или ELK stack
- Используйте Prometheus + Grafana для метрик
- Настройте alerting

## Возвращение к режиму с Telegram ботом

Если нужно вернуть Telegram бота:

```env
TELEGRAM_BOT_ENABLED=true
BOT_TOKEN=your_bot_token
```

Перезапустите приложение, и бот снова заработает параллельно с API.

## Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs -f` или `tail -f logs/bot.log`
2. Убедитесь, что все зависимости установлены
3. Проверьте настройки `.env` файла
