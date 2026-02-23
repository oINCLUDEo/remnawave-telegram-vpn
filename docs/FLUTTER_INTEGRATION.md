# Flutter Application Integration Guide

## Обзор

Этот документ описывает интеграцию Flutter мобильного приложения с существующей backend инфраструктурой Remnawave Telegram VPN бота. Backend уже предоставляет полнофункциональный REST API через Cabinet и WebAPI модули.

## Архитектура

```
┌─────────────────┐
│  Flutter App    │
│  (iOS/Android)  │
└────────┬────────┘
         │ HTTPS/REST
         ↓
┌─────────────────┐
│  FastAPI Server │
│  (/cabinet API) │
├─────────────────┤
│  - Auth         │
│  - Subscriptions│
│  - Payments     │
│  - Balance      │
│  - Referrals    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   PostgreSQL    │
│   Database      │
└─────────────────┘
```

## Основные возможности API

### 1. Аутентификация

Backend поддерживает несколько методов аутентификации:
- **Telegram Widget Auth** - аутентификация через Telegram
- **Email/Password** - регистрация и вход по email
- **OAuth Providers** - поддержка внешних провайдеров

#### Endpoints

##### POST `/cabinet/auth/telegram-widget`
Аутентификация через Telegram Login Widget.

**Request:**
```json
{
  "id": 123456789,
  "first_name": "John",
  "username": "johndoe",
  "auth_date": 1234567890,
  "hash": "abc123..."
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "telegram_id": 123456789,
    "username": "johndoe",
    "first_name": "John",
    "email": null,
    "balance_rubles": 0,
    "referral_code": "ABC123"
  }
}
```

##### POST `/cabinet/auth/register-email`
Регистрация нового пользователя по email.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "first_name": "John",
  "referral_code": "INVITE123",
  "campaign_start_param": "promo_campaign"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "email_verification_required": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "balance_rubles": 0,
    "referral_code": "ABC123"
  },
  "campaign_bonus": {
    "campaign_id": 1,
    "bonus_balance_kopeks": 10000,
    "bonus_days": 7
  }
}
```

##### POST `/cabinet/auth/login-email`
Вход по email и паролю.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "balance_rubles": 0,
    "referral_code": "ABC123"
  }
}
```

##### POST `/cabinet/auth/refresh`
Обновление access token используя refresh token.

**Request:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

##### GET `/cabinet/auth/me`
Получение информации о текущем пользователе.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": 1,
  "telegram_id": 123456789,
  "username": "johndoe",
  "first_name": "John",
  "email": "user@example.com",
  "email_verified": true,
  "balance_rubles": 150.50,
  "balance_kopeks": 15050,
  "referral_code": "ABC123",
  "language": "ru",
  "created_at": "2024-01-01T12:00:00Z",
  "auth_type": "email"
}
```

### 2. Баланс и платежи

#### GET `/cabinet/balance`
Получение текущего баланса пользователя.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "balance_kopeks": 15050,
  "balance_rubles": 150.50
}
```

#### GET `/cabinet/balance/transactions`
История транзакций.

**Query Parameters:**
- `page` (int, default: 1) - номер страницы
- `per_page` (int, default: 20, max: 100) - количество на странице
- `type` (string, optional) - фильтр по типу транзакции

**Response:**
```json
{
  "items": [
    {
      "id": 123,
      "type": "PAYMENT_COMPLETED",
      "amount_kopeks": 50000,
      "amount_rubles": 500.00,
      "description": "Пополнение баланса",
      "created_at": "2024-01-01T12:00:00Z",
      "payment_method": "YOOKASSA_SBP"
    }
  ],
  "total": 45,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

#### POST `/cabinet/balance/top-up`
Создание платежа для пополнения баланса.

**Request:**
```json
{
  "amount_rubles": 500,
  "payment_method": "YOOKASSA_SBP",
  "return_url": "myapp://payment/callback"
}
```

**Response:**
```json
{
  "payment_id": "uuid-here",
  "confirmation_url": "https://yookassa.ru/checkout/...",
  "amount_kopeks": 50000,
  "amount_rubles": 500.00,
  "payment_method": "YOOKASSA_SBP"
}
```

#### GET `/cabinet/balance/payment-methods`
Получение списка доступных методов оплаты.

**Response:**
```json
{
  "methods": [
    {
      "id": "YOOKASSA_SBP",
      "name": "ЮKassa СБП",
      "enabled": true,
      "min_amount_kopeks": 10000,
      "min_amount_rubles": 100.00,
      "currencies": ["RUB"],
      "icon_url": "/media/payment-icons/yookassa_sbp.png"
    },
    {
      "id": "TELEGRAM_STARS",
      "name": "Telegram Stars",
      "enabled": true,
      "min_amount_kopeks": 5000,
      "min_amount_rubles": 50.00,
      "currencies": ["XTR"],
      "icon_url": "/media/payment-icons/telegram_stars.png"
    }
  ]
}
```

#### POST `/cabinet/balance/stars-invoice`
Создание invoice для оплаты Telegram Stars.

**Request:**
```json
{
  "amount_rubles": 100
}
```

**Response:**
```json
{
  "invoice_link": "https://t.me/$abc123...",
  "amount_rubles": 100.00,
  "amount_stars": 200
}
```

### 3. Подписки (Subscriptions)

#### GET `/cabinet/subscription`
Получение текущей подписки пользователя.

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "panel_sub_uuid": "uuid-here",
  "server_squad_id": 1,
  "server_info": {
    "id": 1,
    "name": "RU Server 1",
    "country": "RU",
    "flag": "🇷🇺"
  },
  "is_active": true,
  "is_trial": false,
  "expires_at": "2024-12-31T23:59:59Z",
  "data_limit_bytes": 107374182400,
  "data_usage_bytes": 5368709120,
  "data_remaining_bytes": 102005473280,
  "devices_count": 3,
  "max_devices": 5,
  "autopay_enabled": false
}
```

#### GET `/cabinet/subscription/status`
Проверка статуса подписки.

**Response:**
```json
{
  "has_subscription": true,
  "is_trial": false,
  "is_active": true,
  "days_left": 25,
  "gb_left": 95.5
}
```

#### GET `/cabinet/subscription/trial-info`
Информация о доступности триал периода.

**Response:**
```json
{
  "available": true,
  "days": 3,
  "gb": 5,
  "requires_channel_subscription": true,
  "channel_username": "vpn_channel"
}
```

#### POST `/cabinet/subscription/activate-trial`
Активация триал подписки.

**Request:**
```json
{
  "server_squad_uuid": "uuid-here",
  "devices_count": 2
}
```

**Response:**
```json
{
  "success": true,
  "subscription": {
    "id": 1,
    "expires_at": "2024-01-04T12:00:00Z",
    "data_limit_gb": 5,
    "devices_count": 2
  },
  "config_link": "vless://..."
}
```

#### GET `/cabinet/subscription/tariffs`
Список доступных тарифов.

**Response:**
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
      "discount_percent": 0,
      "max_devices": 3,
      "is_popular": false
    },
    {
      "id": 2,
      "name": "Стандарт",
      "description": "Оптимальный выбор",
      "period_days": 30,
      "data_limit_gb": null,
      "price_kopeks": 49900,
      "price_rubles": 499.00,
      "discount_percent": 10,
      "max_devices": 5,
      "is_popular": true
    }
  ]
}
```

#### POST `/cabinet/subscription/purchase-tariff`
Покупка подписки по тарифу.

**Request:**
```json
{
  "tariff_id": 2,
  "server_squad_uuid": "uuid-here"
}
```

**Response:**
```json
{
  "success": true,
  "subscription": {
    "id": 1,
    "expires_at": "2024-02-01T12:00:00Z",
    "data_limit_gb": null
  },
  "balance_after": 0,
  "transaction_id": 123
}
```

#### POST `/cabinet/subscription/renew`
Продление текущей подписки.

**Request:**
```json
{
  "period_days": 30,
  "gb_amount": 100
}
```

**Response:**
```json
{
  "success": true,
  "new_expires_at": "2024-03-01T12:00:00Z",
  "balance_after": 20050,
  "amount_paid_kopeks": 29900
}
```

### 4. Реферальная система

#### GET `/cabinet/referral/stats`
Статистика реферальной программы.

**Response:**
```json
{
  "referral_code": "ABC123",
  "total_referrals": 15,
  "active_referrals": 10,
  "total_earned_kopeks": 150000,
  "total_earned_rubles": 1500.00,
  "available_for_withdrawal_kopeks": 50000,
  "available_for_withdrawal_rubles": 500.00,
  "referral_link": "https://t.me/bot?start=ref_ABC123"
}
```

#### GET `/cabinet/referral/referrals`
Список рефералов.

**Query Parameters:**
- `page` (int, default: 1)
- `per_page` (int, default: 20)

**Response:**
```json
{
  "referrals": [
    {
      "id": 2,
      "username": "user123",
      "first_name": "Ivan",
      "registered_at": "2024-01-15T10:00:00Z",
      "has_subscription": true,
      "earned_from_user_kopeks": 15000,
      "earned_from_user_rubles": 150.00
    }
  ],
  "total": 15,
  "page": 1,
  "pages": 1
}
```

### 5. Промокоды

#### POST `/cabinet/promocode/activate`
Активация промокода.

**Request:**
```json
{
  "code": "NEWUSER2024"
}
```

**Response:**
```json
{
  "success": true,
  "promo_type": "balance",
  "bonus_balance_kopeks": 50000,
  "bonus_balance_rubles": 500.00,
  "bonus_days": 0,
  "message": "Промокод успешно активирован! Начислено 500 руб."
}
```

### 6. Поддержка (Tickets)

#### GET `/cabinet/tickets`
Список тикетов пользователя.

**Response:**
```json
{
  "tickets": [
    {
      "id": 1,
      "subject": "Проблема с подключением",
      "status": "open",
      "created_at": "2024-01-20T14:00:00Z",
      "updated_at": "2024-01-20T15:30:00Z",
      "unread_messages": 2
    }
  ]
}
```

#### POST `/cabinet/tickets`
Создание нового тикета.

**Request:**
```json
{
  "subject": "Проблема с подключением",
  "message": "Не могу подключиться к серверу RU-1"
}
```

**Response:**
```json
{
  "id": 1,
  "subject": "Проблема с подключением",
  "status": "open",
  "created_at": "2024-01-20T14:00:00Z"
}
```

#### GET `/cabinet/tickets/{ticket_id}/messages`
Получение сообщений в тикете.

**Response:**
```json
{
  "messages": [
    {
      "id": 1,
      "ticket_id": 1,
      "from_admin": false,
      "message": "Не могу подключиться к серверу RU-1",
      "created_at": "2024-01-20T14:00:00Z"
    },
    {
      "id": 2,
      "ticket_id": 1,
      "from_admin": true,
      "message": "Проверьте настройки приложения",
      "created_at": "2024-01-20T15:30:00Z"
    }
  ]
}
```

#### POST `/cabinet/tickets/{ticket_id}/messages`
Отправка сообщения в тикет.

**Request:**
```json
{
  "message": "Спасибо, проблема решена!"
}
```

## Настройка Flutter приложения

### 1. Переменные окружения

Добавьте в `.env` файл сервера:

```env
# Cabinet API
CABINET_ENABLED=true
CABINET_JWT_SECRET=your-secret-key-here
CABINET_ACCESS_TOKEN_EXPIRE_MINUTES=15
CABINET_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS для Flutter app
CABINET_ALLOWED_ORIGINS=myapp://,https://yourdomain.com

# Email верификация (опционально)
CABINET_EMAIL_VERIFICATION_ENABLED=true
CABINET_EMAIL_VERIFICATION_EXPIRE_HOURS=24

# SMTP для email (если используется)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=VPN Service
SMTP_USE_TLS=true
```

### 2. Base URL

API доступен по адресу:
```
https://your-domain.com/cabinet
```

Для локальной разработки:
```
http://localhost:8000/cabinet
```

### 3. Аутентификация в Flutter

Пример реализации HTTP клиента с JWT:

```dart
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiClient {
  final Dio _dio;
  final FlutterSecureStorage _storage;
  
  ApiClient({
    required String baseUrl,
  }) : _dio = Dio(BaseOptions(
         baseUrl: baseUrl,
         connectTimeout: Duration(seconds: 30),
         receiveTimeout: Duration(seconds: 30),
       )),
       _storage = const FlutterSecureStorage() {
    _setupInterceptors();
  }
  
  void _setupInterceptors() {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        // Добавляем access token к каждому запросу
        final token = await _storage.read(key: 'access_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        // Обработка 401 ошибки - обновление токена
        if (error.response?.statusCode == 401) {
          final refreshToken = await _storage.read(key: 'refresh_token');
          if (refreshToken != null) {
            try {
              // Обновляем токен
              final response = await _dio.post('/auth/refresh', data: {
                'refresh_token': refreshToken,
              });
              
              final newToken = response.data['access_token'];
              await _storage.write(key: 'access_token', value: newToken);
              
              // Повторяем оригинальный запрос
              error.requestOptions.headers['Authorization'] = 'Bearer $newToken';
              return handler.resolve(await _dio.fetch(error.requestOptions));
            } catch (e) {
              // Не удалось обновить токен - выходим
              await _storage.deleteAll();
              handler.next(error);
            }
          }
        }
        handler.next(error);
      },
    ));
  }
  
  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await _dio.post('/auth/login-email', data: {
      'email': email,
      'password': password,
    });
    
    // Сохраняем токены
    await _storage.write(
      key: 'access_token',
      value: response.data['access_token'],
    );
    await _storage.write(
      key: 'refresh_token',
      value: response.data['refresh_token'],
    );
    
    return response.data;
  }
  
  Future<Map<String, dynamic>> getBalance() async {
    final response = await _dio.get('/balance');
    return response.data;
  }
  
  Future<Map<String, dynamic>> getSubscription() async {
    final response = await _dio.get('/subscription');
    return response.data;
  }
}
```

### 4. Обработка Deep Links для платежей

Для обработки возврата из платежных систем:

#### iOS (Info.plist)
```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleTypeRole</key>
    <string>Editor</string>
    <key>CFBundleURLName</key>
    <string>com.yourdomain.vpn</string>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>myapp</string>
    </array>
  </dict>
</array>
```

#### Android (AndroidManifest.xml)
```xml
<intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="myapp" />
</intent-filter>
```

#### Flutter код
```dart
import 'package:uni_links/uni_links.dart';

class DeepLinkHandler {
  StreamSubscription? _sub;
  
  void initialize() {
    _sub = uriLinkStream.listen((Uri? uri) {
      if (uri != null) {
        _handleDeepLink(uri);
      }
    });
  }
  
  void _handleDeepLink(Uri uri) {
    if (uri.scheme == 'myapp' && uri.host == 'payment') {
      // Обработка возврата из платежной системы
      final status = uri.queryParameters['status'];
      final paymentId = uri.queryParameters['payment_id'];
      
      if (status == 'success') {
        // Показываем успешное пополнение
        _showPaymentSuccess(paymentId);
      } else {
        // Показываем ошибку
        _showPaymentError();
      }
    }
  }
  
  void dispose() {
    _sub?.cancel();
  }
}
```

## Интеграция платежных систем

### YooKassa СБП

1. Backend уже настроен для работы с YooKassa
2. При создании платежа указывайте `return_url` как deep link вашего приложения
3. Пользователь будет перенаправлен в банковское приложение для оплаты
4. После оплаты вернется в приложение по указанному deep link

**Пример:**
```dart
Future<void> topUpBalance(double amount) async {
  final response = await apiClient.post('/balance/top-up', data: {
    'amount_rubles': amount,
    'payment_method': 'YOOKASSA_SBP',
    'return_url': 'myapp://payment/callback',
  });
  
  final confirmationUrl = response.data['confirmation_url'];
  
  // Открываем браузер или WebView для оплаты
  await launchUrl(Uri.parse(confirmationUrl));
}
```

### Telegram Stars

Для интеграции Telegram Stars в Flutter приложении:

1. Используйте Telegram Mini App API
2. Или создавайте invoice через backend API

**Пример через backend:**
```dart
Future<void> payWithStars(double amount) async {
  final response = await apiClient.post('/balance/stars-invoice', data: {
    'amount_rubles': amount,
  });
  
  final invoiceLink = response.data['invoice_link'];
  
  // Открываем Telegram с invoice
  await launchUrl(Uri.parse(invoiceLink));
}
```

## WebSocket для real-time уведомлений

Backend поддерживает WebSocket соединения для получения уведомлений в реальном времени.

**Endpoint:** `wss://your-domain.com/cabinet/ws`

**Пример подключения:**
```dart
import 'package:web_socket_channel/web_socket_channel.dart';

class NotificationService {
  WebSocketChannel? _channel;
  
  Future<void> connect(String accessToken) async {
    _channel = WebSocketChannel.connect(
      Uri.parse('wss://your-domain.com/cabinet/ws?token=$accessToken'),
    );
    
    _channel!.stream.listen((message) {
      final data = jsonDecode(message);
      _handleNotification(data);
    });
  }
  
  void _handleNotification(Map<String, dynamic> data) {
    switch (data['type']) {
      case 'payment_completed':
        // Показываем уведомление о пополнении
        break;
      case 'subscription_renewed':
        // Уведомление о продлении подписки
        break;
      case 'ticket_reply':
        // Новое сообщение в тикете
        break;
    }
  }
  
  void dispose() {
    _channel?.sink.close();
  }
}
```

## Безопасность

### 1. Хранение токенов
- Используйте `flutter_secure_storage` для безопасного хранения JWT токенов
- Никогда не храните токены в SharedPreferences или обычных файлах

### 2. SSL Pinning
Для дополнительной безопасности реализуйте SSL pinning:

```dart
import 'package:dio/dio.dart';
import 'package:dio/io.dart';

void setupSslPinning(Dio dio) {
  (dio.httpClientAdapter as IOHttpClientAdapter).onHttpClientCreate = (client) {
    client.badCertificateCallback = (cert, host, port) {
      // Проверяем сертификат
      return cert.sha256.toString() == 'YOUR_CERT_SHA256';
    };
    return client;
  };
}
```

### 3. Обфускация кода
При сборке release версии используйте обфускацию:

```bash
flutter build apk --obfuscate --split-debug-info=build/app/outputs/symbols
flutter build ios --obfuscate --split-debug-info=build/ios/outputs/symbols
```

## Тестирование

### 1. Локальная разработка

Запустите backend локально:
```bash
docker-compose -f docker-compose.local.yml up -d
```

Backend будет доступен на `http://localhost:8000`

### 2. Тестовые данные

Создайте тестового пользователя через API:
```bash
curl -X POST http://localhost:8000/cabinet/auth/register-email \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "first_name": "Test User"
  }'
```

## Развертывание

### 1. Backend
Backend уже готов к работе. Убедитесь что:
- `CABINET_ENABLED=true` в `.env`
- Настроены CORS origins для вашего домена
- SSL сертификаты настроены правильно

### 2. Flutter App

Для production сборки:

**Android:**
```bash
flutter build apk --release
# или
flutter build appbundle --release
```

**iOS:**
```bash
flutter build ipa --release
```

## API документация (OpenAPI)

Backend автоматически генерирует OpenAPI документацию, доступную по адресу:
- Swagger UI: `https://your-domain.com/docs`
- ReDoc: `https://your-domain.com/redoc`
- OpenAPI JSON: `https://your-domain.com/openapi.json`

Используйте эту документацию для генерации клиентского кода:
```bash
# Установите openapi-generator
npm install -g @openapitools/openapi-generator-cli

# Сгенерируйте Dart клиент
openapi-generator-cli generate \
  -i https://your-domain.com/openapi.json \
  -g dart-dio \
  -o lib/api_client
```

## Миграция с Telegram бота

Пользователи могут мигрировать с Telegram бота на Flutter приложение:

1. **Вход через Telegram** - используйте Telegram Widget Auth
2. **Автоматический перенос данных** - все подписки, баланс и история сохраняются
3. **Реферальная система** - реферальные ссылки работают в обоих интерфейсах

## Дополнительные ресурсы

- **Backend репозиторий:** https://github.com/oINCLUDEo/remnawave-telegram-vpn
- **Cabinet WebApp:** https://github.com/BEDOLAGA-DEV/bedolaga-cabinet/
- **Telegram бот:** https://t.me/zero_ping_vpn_bot
- **Чат поддержки:** https://t.me/+wTdMtSWq8YdmZmVi

## Поддержка

Если у вас возникли вопросы:
1. Изучите документацию API на `/docs`
2. Проверьте логи backend сервера
3. Задайте вопрос в чате Bedolaga: https://t.me/+wTdMtSWq8YdmZmVi

## Лицензия

MIT License - см. LICENSE файл в репозитории.
