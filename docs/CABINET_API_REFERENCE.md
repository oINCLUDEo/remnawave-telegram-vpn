# Cabinet API Reference

Полная справочная документация по Cabinet API endpoints.

## Base URL

```
http://localhost:8081
```

Для Android эмулятора используйте `http://10.0.2.2:8081`.

---

## Аутентификация

### POST /cabinet/auth/email/login

Вход с email и паролем.

**Требует токен**: Нет

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "password123",
  "device_info": {
    "platform": "android",
    "app_version": "1.0.0"
  }
}
```

**Response (200)**:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 123,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "telegram_id": null,
    "language": "ru",
    "created_at": "2026-02-23T12:00:00Z"
  }
}
```

**Errors**:
- `400` - Неверный email или пароль
- `401` - Email не верифицирован
- `404` - Пользователь не найден

**Example**:
```bash
curl http://localhost:8081/cabinet/auth/email/login -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

---

### POST /cabinet/auth/email/register/standalone

Регистрация нового пользователя с email и паролем.

**Требует токен**: Нет

**Request Body**:
```json
{
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "language": "ru",
  "device_info": {
    "platform": "android",
    "app_version": "1.0.0"
  }
}
```

**Response (201)**:
```json
{
  "message": "Registration successful. Please check your email for verification link.",
  "requires_verification": true,
  "user_id": 123
}
```

**Или сразу с токенами (если тестовый email)**:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 123,
    "email": "newuser@example.com",
    "first_name": "John"
  }
}
```

**Errors**:
- `400` - Email уже зарегистрирован
- `400` - Слабый пароль
- `400` - Недопустимый домен email (disposable email)

**Example**:
```bash
curl http://localhost:8081/cabinet/auth/email/register/standalone -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "language": "ru"
  }'
```

---

### POST /cabinet/auth/refresh

Обновление access token с помощью refresh token.

**Требует токен**: Нет (использует refresh_token)

**Request Body**:
```json
{
  "refresh_token": "eyJ..."
}
```

**Response (200)**:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Errors**:
- `401` - Invalid or expired refresh token

**Example**:
```bash
curl http://localhost:8081/cabinet/auth/refresh -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

---

### POST /cabinet/auth/logout

Выход из системы (инвалидация токенов).

**Требует токен**: Да

**Request Body**: Нет

**Response (200)**:
```json
{
  "message": "Logged out successfully"
}
```

**Example**:
```bash
curl http://localhost:8081/cabinet/auth/logout -X POST \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### GET /cabinet/auth/me

Получить информацию о текущем пользователе.

**Требует токен**: Да

**Response (200)**:
```json
{
  "id": 123,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "telegram_id": 123456789,
  "username": null,
  "language": "ru",
  "referral_code": "ABC123",
  "balance_kopeks": 50000,
  "created_at": "2026-02-23T12:00:00Z"
}
```

**Example**:
```bash
curl http://localhost:8081/cabinet/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Подписки

### GET /cabinet/subscription/current

Получить текущую подписку пользователя.

**Требует токен**: Да

**Response (200)**:
```json
{
  "id": 456,
  "user_id": 123,
  "status": "active",
  "trial": false,
  "expires_at": "2026-03-23T12:00:00Z",
  "traffic_limit_bytes": 107374182400,
  "traffic_used_bytes": 5368709120,
  "device_limit": 3,
  "devices_connected": 2,
  "auto_renew": true
}
```

**Errors**:
- `404` - No active subscription

**Example**:
```bash
curl http://localhost:8081/cabinet/subscription/current \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### GET /cabinet/subscription/link

Получить ссылку подключения для VPN.

**Требует токен**: Да

**Response (200)**:
```json
{
  "link": "vless://uuid@server.example.com:443?...",
  "qr_code": "data:image/png;base64,..."
}
```

**Example**:
```bash
curl http://localhost:8081/cabinet/subscription/link \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### GET /cabinet/subscription/config

Получить конфигурацию подписки для VPN клиента.

**Требует токен**: Да

**Response (200)**:
```text
# VPN конфигурация
...
```

**Example**:
```bash
curl http://localhost:8081/cabinet/subscription/config \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Баланс

### GET /cabinet/balance

Получить баланс пользователя.

**Требует токен**: Да

**Response (200)**:
```json
{
  "balance_kopeks": 50000,
  "balance_rub": 500.00,
  "currency": "RUB"
}
```

**Example**:
```bash
curl http://localhost:8081/cabinet/balance \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### GET /cabinet/balance/transactions

История транзакций пользователя.

**Требует токен**: Да

**Query Parameters**:
- `limit` (optional): Количество записей (default: 20)
- `offset` (optional): Смещение (default: 0)

**Response (200)**:
```json
{
  "transactions": [
    {
      "id": 789,
      "type": "payment",
      "amount_kopeks": 100000,
      "description": "Пополнение баланса",
      "created_at": "2026-02-23T12:00:00Z"
    }
  ],
  "total": 1
}
```

**Example**:
```bash
curl "http://localhost:8081/cabinet/balance/transactions?limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Реферальная система

### GET /cabinet/referral/info

Получить информацию о реферальной программе.

**Требует токен**: Да

**Response (200)**:
```json
{
  "referral_code": "ABC123",
  "referral_link": "https://t.me/bot?start=ABC123",
  "referrals_count": 5,
  "earnings_kopeks": 25000
}
```

**Example**:
```bash
curl http://localhost:8081/cabinet/referral/info \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Серверы

### GET /cabinet/info/servers

Получить список доступных VPN серверов.

**Требует токен**: Да (опционально)

**Response (200)**:
```json
{
  "servers": [
    {
      "id": 1,
      "name": "Netherlands - Amsterdam",
      "country_code": "NL",
      "city": "Amsterdam",
      "load": 45,
      "status": "online"
    }
  ]
}
```

**Example**:
```bash
curl http://localhost:8081/cabinet/info/servers \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Брендинг

### GET /cabinet/branding/email-auth

Проверить доступность email аутентификации.

**Требует токен**: Нет

**Response (200)**:
```json
{
  "enabled": true
}
```

**Example**:
```bash
curl http://localhost:8081/cabinet/branding/email-auth
```

---

## Общие ошибки

### 401 Unauthorized
```json
{
  "detail": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
  "detail": "Access denied"
}
```

### 404 Not Found
```json
{
  "detail": "Not Found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Аутентификация в запросах

Все защищенные endpoints требуют Bearer token в заголовке:

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Access token действителен 1 час. Используйте refresh token для получения нового access token.

---

## CORS

Для локальной разработки установите в `.env`:

```env
CABINET_ALLOWED_ORIGINS=*
```

Для production укажите конкретные домены:

```env
CABINET_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

---

## Тестовые аккаунты

Если в `.env` настроены тестовые email аккаунты:

```env
TEST_EMAIL=test@example.com:password123
```

То при регистрации/входе с этим email:
- Email verification автоматически пройден
- Можно сразу войти после регистрации

---

## Дополнительная информация

- Все даты в формате ISO 8601 UTC
- Суммы в копейках (100 копеек = 1 рубль)
- Трафик в байтах (1 GB = 1073741824 bytes)
- Токены в формате JWT

---

## Swagger UI

Интерактивная документация API доступна по адресу:

```
http://localhost:8081/docs
```

Убедитесь что `WEB_API_DOCS_ENABLED=true` в `.env`.
