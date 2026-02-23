# API Reference для Flutter приложения

## Общая информация

**Base URL:** `https://your-domain.com/cabinet`

**Authentication:** Bearer Token (JWT)

**Content-Type:** `application/json`

## Структура ответов

### Успешный ответ
```json
{
  "field1": "value1",
  "field2": "value2"
}
```

### Ошибка
```json
{
  "detail": "Error message"
}
```

## HTTP статус коды

- `200 OK` - Успешный запрос
- `201 Created` - Ресурс создан
- `400 Bad Request` - Неверные параметры
- `401 Unauthorized` - Не авторизован
- `403 Forbidden` - Нет доступа
- `404 Not Found` - Ресурс не найден
- `422 Unprocessable Entity` - Ошибка валидации
- `500 Internal Server Error` - Ошибка сервера

---

## Аутентификация

### POST /auth/register-email

Регистрация нового пользователя по email.

**Request Body:**
```json
{
  "email": "string (email format, required)",
  "password": "string (min 8 chars, required)",
  "first_name": "string (required)",
  "last_name": "string (optional)",
  "referral_code": "string (optional)",
  "campaign_start_param": "string (optional)"
}
```

**Response 200:**
```json
{
  "message": "User registered successfully",
  "email_verification_required": true,
  "user": {
    "id": 1,
    "telegram_id": null,
    "username": null,
    "first_name": "John",
    "last_name": null,
    "email": "user@example.com",
    "email_verified": false,
    "balance_kopeks": 0,
    "balance_rubles": 0.0,
    "referral_code": "ABC123XYZ",
    "language": "ru",
    "created_at": "2024-01-01T12:00:00Z",
    "auth_type": "email"
  },
  "campaign_bonus": {
    "campaign_id": 1,
    "bonus_balance_kopeks": 10000,
    "bonus_days": 7
  }
}
```

**Response 400:**
```json
{
  "detail": "Email already registered"
}
```

---

### POST /auth/register-email-standalone

Регистрация standalone пользователя (без реферала/кампании).

**Request Body:**
```json
{
  "email": "string (email format, required)",
  "password": "string (min 8 chars, required)",
  "first_name": "string (required)",
  "last_name": "string (optional)"
}
```

**Response:** Аналогично `/auth/register-email`

---

### POST /auth/login-email

Вход по email и паролю.

**Request Body:**
```json
{
  "email": "string (required)",
  "password": "string (required)"
}
```

**Response 200:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "balance_rubles": 150.50,
    "referral_code": "ABC123XYZ"
  }
}
```

**Response 401:**
```json
{
  "detail": "Invalid email or password"
}
```

---

### POST /auth/telegram-widget

Аутентификация через Telegram Login Widget.

**Request Body:**
```json
{
  "id": 123456789,
  "first_name": "John",
  "last_name": "Doe",
  "username": "johndoe",
  "photo_url": "https://...",
  "auth_date": 1234567890,
  "hash": "abc123..."
}
```

**Response:** Аналогично `/auth/login-email`

---

### POST /auth/telegram-miniapp

Аутентификация через Telegram Mini App (initData).

**Request Body:**
```json
{
  "init_data": "query_id=...&user=...&auth_date=...&hash=...",
  "referral_code": "string (optional)",
  "campaign_start_param": "string (optional)"
}
```

**Response:** Аналогично `/auth/login-email`

---

### POST /auth/refresh

Обновление access token.

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response 200:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

---

### GET /auth/me

Получение информации о текущем пользователе.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response 200:**
```json
{
  "id": 1,
  "telegram_id": 123456789,
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "email": "user@example.com",
  "email_verified": true,
  "balance_kopeks": 15050,
  "balance_rubles": 150.50,
  "referral_code": "ABC123XYZ",
  "language": "ru",
  "created_at": "2024-01-01T12:00:00Z",
  "auth_type": "email"
}
```

---

### POST /auth/verify-email

Верификация email через код.

**Request Body:**
```json
{
  "verification_token": "string"
}
```

**Response 200:**
```json
{
  "message": "Email verified successfully"
}
```

---

### POST /auth/forgot-password

Запрос на сброс пароля.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response 200:**
```json
{
  "message": "Password reset instructions sent to email"
}
```

---

### POST /auth/reset-password

Сброс пароля по токену.

**Request Body:**
```json
{
  "reset_token": "string",
  "new_password": "string (min 8 chars)"
}
```

**Response 200:**
```json
{
  "message": "Password reset successfully"
}
```

---

## Баланс

### GET /balance

Получение текущего баланса.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "balance_kopeks": 15050,
  "balance_rubles": 150.50
}
```

---

### GET /balance/transactions

История транзакций.

**Query Parameters:**
- `page` (int, default: 1) - номер страницы
- `per_page` (int, default: 20, max: 100) - элементов на странице
- `type` (string, optional) - фильтр по типу

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "items": [
    {
      "id": 123,
      "type": "PAYMENT_COMPLETED",
      "amount_kopeks": 50000,
      "amount_rubles": 500.00,
      "description": "Пополнение баланса",
      "created_at": "2024-01-15T10:30:00Z",
      "payment_method": "YOOKASSA_SBP"
    },
    {
      "id": 122,
      "type": "SUBSCRIPTION_PURCHASE",
      "amount_kopeks": -29900,
      "amount_rubles": -299.00,
      "description": "Покупка подписки на 30 дней",
      "created_at": "2024-01-14T15:20:00Z",
      "payment_method": null
    }
  ],
  "total": 45,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

---

### GET /balance/payment-methods

Список доступных методов оплаты.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "methods": [
    {
      "id": "YOOKASSA_SBP",
      "name": "ЮKassa СБП",
      "enabled": true,
      "min_amount_kopeks": 10000,
      "min_amount_rubles": 100.00,
      "max_amount_kopeks": null,
      "max_amount_rubles": null,
      "currencies": ["RUB"],
      "icon_url": "/media/payment-icons/yookassa_sbp.png",
      "description": "Оплата через Систему Быстрых Платежей"
    },
    {
      "id": "TELEGRAM_STARS",
      "name": "Telegram Stars",
      "enabled": true,
      "min_amount_kopeks": 5000,
      "min_amount_rubles": 50.00,
      "max_amount_kopeks": 250000,
      "max_amount_rubles": 2500.00,
      "currencies": ["XTR"],
      "icon_url": "/media/payment-icons/telegram_stars.png",
      "description": "Оплата Telegram Stars"
    }
  ]
}
```

---

### POST /balance/top-up

Создание платежа для пополнения баланса.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "amount_rubles": 500,
  "payment_method": "YOOKASSA_SBP",
  "return_url": "myapp://payment/callback"
}
```

**Response 200:**
```json
{
  "payment_id": "2e3f89a4-5b6c-7d8e-9f0a-1b2c3d4e5f6a",
  "confirmation_url": "https://yookassa.ru/checkout/payments/...",
  "amount_kopeks": 50000,
  "amount_rubles": 500.00,
  "payment_method": "YOOKASSA_SBP",
  "status": "pending"
}
```

---

### POST /balance/stars-invoice

Создание invoice для Telegram Stars.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "amount_rubles": 100
}
```

**Response 200:**
```json
{
  "invoice_link": "https://t.me/$abc123...",
  "amount_rubles": 100.00,
  "amount_stars": 200
}
```

---

### GET /balance/pending-payments

Список ожидающих платежей.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "payments": [
    {
      "payment_id": "uuid",
      "amount_kopeks": 50000,
      "amount_rubles": 500.00,
      "payment_method": "YOOKASSA_SBP",
      "created_at": "2024-01-15T10:30:00Z",
      "can_check_manually": true
    }
  ]
}
```

---

### POST /balance/check-payment/{payment_id}

Ручная проверка статуса платежа.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "status": "completed",
  "message": "Payment verified successfully"
}
```

---

## Подписки

### GET /subscription

Получение текущей подписки.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "id": 1,
  "user_id": 1,
  "panel_sub_uuid": "abc-123-def-456",
  "server_squad_id": 1,
  "server_info": {
    "id": 1,
    "name": "RU Server 1",
    "country": "RU",
    "flag": "🇷🇺",
    "panel_squad_uuid": "squad-uuid"
  },
  "is_active": true,
  "is_trial": false,
  "expires_at": "2024-12-31T23:59:59Z",
  "data_limit_bytes": 107374182400,
  "data_usage_bytes": 5368709120,
  "data_remaining_bytes": 102005473280,
  "data_limit_gb": 100,
  "data_usage_gb": 5.0,
  "data_remaining_gb": 95.0,
  "devices_count": 3,
  "max_devices": 5,
  "autopay_enabled": false,
  "config_link": "vless://...",
  "qr_code_base64": "data:image/png;base64,..."
}
```

**Response 404:**
```json
{
  "detail": "No active subscription found"
}
```

---

### GET /subscription/status

Краткий статус подписки.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "has_subscription": true,
  "is_trial": false,
  "is_active": true,
  "expires_at": "2024-12-31T23:59:59Z",
  "days_left": 25,
  "gb_left": 95.5,
  "gb_total": 100
}
```

---

### GET /subscription/trial-info

Информация о триал периоде.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "available": true,
  "days": 3,
  "gb": 5,
  "max_devices": 2,
  "requires_channel_subscription": true,
  "channel_username": "vpn_channel",
  "channel_link": "https://t.me/vpn_channel"
}
```

---

### POST /subscription/activate-trial

Активация триал подписки.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "server_squad_uuid": "squad-uuid",
  "devices_count": 2
}
```

**Response 200:**
```json
{
  "success": true,
  "subscription": {
    "id": 1,
    "expires_at": "2024-01-04T12:00:00Z",
    "data_limit_gb": 5,
    "devices_count": 2,
    "config_link": "vless://...",
    "qr_code_base64": "data:image/png;base64,..."
  }
}
```

---

### GET /subscription/tariffs

Список доступных тарифов.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "tariffs": [
    {
      "id": 1,
      "name": "Базовый",
      "description": "Для начинающих",
      "period_days": 30,
      "data_limit_gb": 100,
      "price_kopeks": 29900,
      "price_rubles": 299.00,
      "original_price_kopeks": 29900,
      "discount_percent": 0,
      "max_devices": 3,
      "is_popular": false,
      "is_unlimited": false,
      "sort_order": 1
    },
    {
      "id": 2,
      "name": "Стандарт",
      "description": "Оптимальный выбор",
      "period_days": 30,
      "data_limit_gb": null,
      "price_kopeks": 44910,
      "price_rubles": 449.10,
      "original_price_kopeks": 49900,
      "discount_percent": 10,
      "max_devices": 5,
      "is_popular": true,
      "is_unlimited": true,
      "sort_order": 2
    }
  ]
}
```

---

### POST /subscription/purchase-tariff

Покупка подписки по тарифу.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "tariff_id": 2,
  "server_squad_uuid": "squad-uuid"
}
```

**Response 200:**
```json
{
  "success": true,
  "subscription": {
    "id": 1,
    "expires_at": "2024-02-01T12:00:00Z",
    "data_limit_gb": null,
    "config_link": "vless://..."
  },
  "balance_after_kopeks": 0,
  "balance_after_rubles": 0.00,
  "amount_paid_kopeks": 49900,
  "amount_paid_rubles": 499.00,
  "transaction_id": 123
}
```

**Response 400:**
```json
{
  "detail": "Insufficient balance. Required: 499.00 RUB, Available: 150.50 RUB"
}
```

---

### POST /subscription/renew

Продление подписки.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "period_days": 30,
  "gb_amount": 100
}
```

**Response 200:**
```json
{
  "success": true,
  "new_expires_at": "2024-03-01T12:00:00Z",
  "balance_after_kopeks": 20050,
  "balance_after_rubles": 200.50,
  "amount_paid_kopeks": 29900,
  "amount_paid_rubles": 299.00
}
```

---

### GET /subscription/renewal-options

Доступные варианты продления.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "options": [
    {
      "period_days": 30,
      "gb_amount": 50,
      "price_kopeks": 19900,
      "price_rubles": 199.00,
      "discount_percent": 0
    },
    {
      "period_days": 30,
      "gb_amount": 100,
      "price_kopeks": 29900,
      "price_rubles": 299.00,
      "discount_percent": 10
    }
  ]
}
```

---

### POST /subscription/autopay

Управление автоплатежами.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "enabled": true
}
```

**Response 200:**
```json
{
  "success": true,
  "autopay_enabled": true
}
```

---

## Реферальная система

### GET /referral/stats

Статистика рефералов.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "referral_code": "ABC123XYZ",
  "referral_link": "https://t.me/bot?start=ref_ABC123XYZ",
  "total_referrals": 15,
  "active_referrals": 10,
  "trial_converted": 8,
  "total_earned_kopeks": 150000,
  "total_earned_rubles": 1500.00,
  "available_for_withdrawal_kopeks": 50000,
  "available_for_withdrawal_rubles": 500.00,
  "pending_kopeks": 25000,
  "pending_rubles": 250.00
}
```

---

### GET /referral/referrals

Список рефералов.

**Query Parameters:**
- `page` (int, default: 1)
- `per_page` (int, default: 20)

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "referrals": [
    {
      "id": 2,
      "telegram_id": 987654321,
      "username": "user123",
      "first_name": "Ivan",
      "registered_at": "2024-01-15T10:00:00Z",
      "has_subscription": true,
      "subscription_expires_at": "2024-02-15T10:00:00Z",
      "earned_from_user_kopeks": 15000,
      "earned_from_user_rubles": 150.00,
      "status": "active"
    }
  ],
  "total": 15,
  "page": 1,
  "per_page": 20,
  "pages": 1
}
```

---

### GET /referral/earnings

История заработка.

**Query Parameters:**
- `page` (int, default: 1)
- `per_page` (int, default: 20)

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "earnings": [
    {
      "id": 123,
      "referral_user_id": 2,
      "referral_username": "user123",
      "amount_kopeks": 5000,
      "amount_rubles": 50.00,
      "transaction_type": "subscription_purchase",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "pages": 3
}
```

---

## Промокоды

### POST /promocode/activate

Активация промокода.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "code": "NEWUSER2024"
}
```

**Response 200:**
```json
{
  "success": true,
  "promo_type": "balance",
  "bonus_balance_kopeks": 50000,
  "bonus_balance_rubles": 500.00,
  "bonus_days": 0,
  "bonus_gb": 0,
  "message": "Промокод успешно активирован! Начислено 500 руб."
}
```

**Response 400:**
```json
{
  "detail": "Promocode not found or expired"
}
```

---

## Тикеты (Поддержка)

### GET /tickets

Список тикетов пользователя.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "tickets": [
    {
      "id": 1,
      "subject": "Проблема с подключением",
      "status": "open",
      "created_at": "2024-01-20T14:00:00Z",
      "updated_at": "2024-01-20T15:30:00Z",
      "last_message": "Проверьте настройки...",
      "unread_messages": 2
    }
  ]
}
```

---

### POST /tickets

Создание тикета.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "subject": "Проблема с подключением",
  "message": "Не могу подключиться к серверу RU-1"
}
```

**Response 201:**
```json
{
  "id": 1,
  "subject": "Проблема с подключением",
  "status": "open",
  "created_at": "2024-01-20T14:00:00Z"
}
```

---

### GET /tickets/{ticket_id}/messages

Сообщения в тикете.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "messages": [
    {
      "id": 1,
      "ticket_id": 1,
      "from_admin": false,
      "from_user_id": 1,
      "message": "Не могу подключиться к серверу RU-1",
      "created_at": "2024-01-20T14:00:00Z",
      "is_read": true
    },
    {
      "id": 2,
      "ticket_id": 1,
      "from_admin": true,
      "from_user_id": null,
      "message": "Проверьте настройки приложения",
      "created_at": "2024-01-20T15:30:00Z",
      "is_read": false
    }
  ]
}
```

---

### POST /tickets/{ticket_id}/messages

Отправка сообщения.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "message": "Спасибо, проблема решена!"
}
```

**Response 201:**
```json
{
  "id": 3,
  "ticket_id": 1,
  "message": "Спасибо, проблема решена!",
  "created_at": "2024-01-20T16:00:00Z"
}
```

---

### PATCH /tickets/{ticket_id}/close

Закрытие тикета.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "success": true,
  "ticket_id": 1,
  "status": "closed"
}
```

---

## Информация

### GET /info

Общая информация о сервисе.

**Response 200:**
```json
{
  "service_name": "VPN Service",
  "support_email": "support@example.com",
  "support_telegram": "@support_bot",
  "terms_url": "https://example.com/terms",
  "privacy_url": "https://example.com/privacy"
}
```

---

### GET /branding

Брендинг приложения.

**Response 200:**
```json
{
  "logo_url": "/media/logo.png",
  "primary_color": "#0088CC",
  "secondary_color": "#FF6600",
  "app_name": "My VPN"
}
```

---

## WebSocket

### WS /ws

WebSocket соединение для real-time уведомлений.

**Connection URL:**
```
wss://your-domain.com/cabinet/ws?token=<access_token>
```

**Message Format:**
```json
{
  "type": "notification_type",
  "data": {
    "...": "..."
  },
  "timestamp": "2024-01-20T16:00:00Z"
}
```

**Notification Types:**
- `payment_completed` - Платеж завершен
- `subscription_renewed` - Подписка продлена
- `subscription_expires_soon` - Подписка скоро истекает
- `ticket_reply` - Ответ в тикете
- `referral_earned` - Заработок с реферала
- `balance_updated` - Баланс обновлен

**Example:**
```json
{
  "type": "payment_completed",
  "data": {
    "amount_rubles": 500.00,
    "new_balance_rubles": 650.50
  },
  "timestamp": "2024-01-20T16:00:00Z"
}
```

---

## Типы данных

### TransactionType
- `PAYMENT_COMPLETED` - Пополнение баланса
- `SUBSCRIPTION_PURCHASE` - Покупка подписки
- `SUBSCRIPTION_RENEWAL` - Продление подписки
- `REFERRAL_EARNING` - Заработок с реферала
- `WITHDRAWAL` - Вывод средств
- `BONUS` - Бонус
- `REFUND` - Возврат

### PaymentMethod
- `YOOKASSA_SBP` - ЮKassa СБП
- `YOOKASSA_CARD` - ЮKassa карты
- `TELEGRAM_STARS` - Telegram Stars
- `CRYPTOBOT` - CryptoBot
- `TRIBUTE` - Tribute
- `HELEKET` - Heleket
- `MULENPAY_SBP` - MulenPay СБП
- `MULENPAY_CARD` - MulenPay карты
- и другие...

### SubscriptionStatus
- `active` - Активна
- `expired` - Истекла
- `suspended` - Приостановлена

### TicketStatus
- `open` - Открыт
- `in_progress` - В работе
- `closed` - Закрыт

---

## Rate Limits

- **Authentication endpoints:** 5 requests per minute
- **Payment endpoints:** 10 requests per minute
- **Other endpoints:** 60 requests per minute

При превышении лимита возвращается статус `429 Too Many Requests`.

---

## Примеры использования

См. [FLUTTER_QUICKSTART.md](./FLUTTER_QUICKSTART.md) для полных примеров кода.
