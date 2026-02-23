# Flutter Integration - Addition to README.md

## 📱 **Flutter Mobile Application Support**

> **🆕 Интеграция с Flutter приложением**
>
> Backend предоставляет полнофункциональный REST API для создания мобильных приложений на Flutter/React Native/любых других платформах!
>
> **Возможности:**
> - ✅ Полная независимость от Telegram
> - ✅ Собственный брендинг и дизайн
> - ✅ Все функции Telegram бота доступны через API
> - ✅ Email регистрация и аутентификация
> - ✅ YooKassa СБП и Telegram Stars платежи
> - ✅ WebSocket для real-time уведомлений
> - ✅ JWT токены с refresh механизмом
> - ✅ OpenAPI документация (Swagger)

### 🚀 Быстрый старт с Flutter

**1. Активируйте Cabinet API:**

```env
# В файле .env
CABINET_ENABLED=true
CABINET_JWT_SECRET=your-secret-key-min-32-chars
CABINET_ALLOWED_ORIGINS=myapp://,https://yourdomain.com
```

**2. Перезапустите сервер:**

```bash
docker-compose restart
```

**3. API доступен на:**

- REST API: `https://your-domain.com/cabinet`
- Swagger Docs: `https://your-domain.com/docs`
- OpenAPI JSON: `https://your-domain.com/openapi.json`

### 📚 Документация для Flutter разработчиков

Создана полная документация для разработки Flutter приложения:

- **[FLUTTER_QUICKSTART.md](docs/FLUTTER_QUICKSTART.md)** - 5 минут до первого запроса
- **[FLUTTER_INTEGRATION.md](docs/FLUTTER_INTEGRATION.md)** - Полное руководство по интеграции
- **[API_REFERENCE.md](docs/API_REFERENCE.md)** - Детальная документация всех endpoints
- **[FLUTTER_ARCHITECTURE.md](docs/FLUTTER_ARCHITECTURE.md)** - Архитектура и best practices
- **[.env.flutter.example](docs/.env.flutter.example)** - Пример конфигурации

### 🔑 Ключевые API endpoints

```dart
// Аутентификация
POST /cabinet/auth/register-email     // Регистрация
POST /cabinet/auth/login-email         // Вход
POST /cabinet/auth/telegram-widget     // Telegram авторизация
POST /cabinet/auth/refresh             // Обновление токена
GET  /cabinet/auth/me                  // Текущий пользователь

// Баланс и платежи
GET  /cabinet/balance                  // Получить баланс
POST /cabinet/balance/top-up           // Пополнить баланс
GET  /cabinet/balance/payment-methods  // Методы оплаты
POST /cabinet/balance/stars-invoice    // Telegram Stars invoice

// Подписки
GET  /cabinet/subscription             // Текущая подписка
GET  /cabinet/subscription/tariffs     // Доступные тарифы
POST /cabinet/subscription/purchase-tariff  // Купить подписку
POST /cabinet/subscription/activate-trial   // Активировать триал

// Реферальная система
GET  /cabinet/referral/stats           // Статистика
GET  /cabinet/referral/referrals       // Список рефералов

// Поддержка
GET  /cabinet/tickets                  // Список тикетов
POST /cabinet/tickets                  // Создать тикет

// WebSocket
WS   /cabinet/ws                       // Real-time уведомления
```

### 💡 Пример Flutter кода

```dart
import 'package:dio/dio.dart';

class ApiClient {
  static const baseUrl = 'https://your-domain.com/cabinet';
  final dio = Dio(BaseOptions(baseUrl: baseUrl));

  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await dio.post('/auth/login-email', data: {
      'email': email,
      'password': password,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> getBalance(String token) async {
    final response = await dio.get('/balance',
      options: Options(headers: {'Authorization': 'Bearer $token'}),
    );
    return response.data;
  }
}
```

### 🔐 Безопасность

- JWT токены с автоматическим refresh
- HTTPS обязателен для production
- CORS настраивается через `CABINET_ALLOWED_ORIGINS`
- Rate limiting на всех endpoints
- SSL pinning рекомендуется для мобильных приложений

### 🎨 Преимущества Flutter приложения

1. **Независимость от Telegram** - работает даже при блокировке
2. **Полный контроль над UX** - свой дизайн и брендинг
3. **Расширенный функционал** - возможности нативных приложений
4. **Push уведомления** - через Firebase Cloud Messaging
5. **Offline режим** - кэширование данных
6. **App Store / Google Play** - профессиональная дистрибуция

### 🔄 Миграция с Telegram бота

Пользователи могут легко мигрировать:
- Авторизация через Telegram Widget сохраняет все данные
- Email регистрация для новых пользователей
- Вся история, баланс и подписки автоматически доступны
- Реферальные ссылки работают в обоих интерфейсах

### 📊 Поддерживаемые платформы

- ✅ **Flutter** - iOS, Android, Web
- ✅ **React Native** - iOS, Android
- ✅ **Native iOS** - Swift
- ✅ **Native Android** - Kotlin/Java
- ✅ **Web Frontend** - React, Vue, Angular

Backend предоставляет универсальный REST API, совместимый с любой платформой!

---

## 💳 Платежные системы (для Flutter)

### YooKassa (СБП + Карты)

```dart
// Создание платежа
final response = await api.post('/balance/top-up', data: {
  'amount_rubles': 500,
  'payment_method': 'YOOKASSA_SBP',
  'return_url': 'myapp://payment/callback',
});

// Открыть URL для оплаты
final url = response.data['confirmation_url'];
await launchUrl(Uri.parse(url));
```

### Telegram Stars

```dart
// Создание invoice
final response = await api.post('/balance/stars-invoice', data: {
  'amount_rubles': 100,
});

// Открыть Telegram с invoice
final invoiceLink = response.data['invoice_link'];
await launchUrl(Uri.parse(invoiceLink));
```

---
