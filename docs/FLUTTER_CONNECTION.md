# Подключение Flutter приложения к Backend API

## ❌ Ошибка: "ClientException with SocketException connection refused"

Эта ошибка означает что Flutter приложение не может подключиться к backend API.

---

## ✅ Решение (пошагово)

### Шаг 1: Включите Cabinet (Личный кабинет) в backend

Backend **по умолчанию отключает** auth endpoints. Нужно включить Cabinet.

#### Отредактируйте `.env` файл:

```env
# ===== ЛИЧНЫЙ КАБИНЕТ (CABINET) =====
CABINET_ENABLED=true

# Включить регистрацию/вход по email
CABINET_EMAIL_AUTH_ENABLED=true

# Для разработки отключите верификацию email
CABINET_EMAIL_VERIFICATION_ENABLED=false

# Web API должен быть включен
WEB_API_ENABLED=true
WEB_API_HOST=0.0.0.0
WEB_API_PORT=8081

# Разрешенные origins для CORS (для Flutter приложения)
CABINET_ALLOWED_ORIGINS=*
```

#### Перезапустите backend:

```bash
# Если запускаете через Python
python main.py

# Если через Docker Compose
docker-compose -f docker-compose.local.yml restart bot
```

---

### Шаг 2: Настройте правильный API URL в Flutter

#### A. Для Android Эмулятора

Android эмулятор **не может использовать `localhost`**. Используйте `10.0.2.2`:

```bash
cd flutter_app/ulya_vpn
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8081
```

#### B. Для физического Android/iOS устройства

Используйте IP адрес вашего компьютера:

```bash
# Узнайте ваш IP
ipconfig  # Windows
ifconfig  # Linux/Mac

# Например, если IP: 192.168.1.100
flutter run --dart-define=API_BASE_URL=http://192.168.1.100:8081
```

#### C. Для iOS Simulator

iOS simulator может использовать `localhost`:

```bash
flutter run --dart-define=API_BASE_URL=http://localhost:8081
```

---

### Шаг 3: Проверьте что backend работает

```bash
# Проверьте что API отвечает (unified health endpoint)
curl http://localhost:8081/health/unified

# Или через браузер
http://localhost:8081/health/unified
```

Должно вернуть JSON ответ с информацией о состоянии системы.

**Важно**: Endpoint `/api/health` требует API токен. Для простой проверки используйте `/health/unified`.

---

## 🔍 Диагностика проблемы

### Проверка 1: Backend запущен?

```bash
# Для Docker
docker ps | findstr bot

# Для Python
# Должен быть запущен python main.py
```

### Проверка 2: Порт 8081 открыт?

```bash
netstat -an | findstr :8081
```

Должна быть строка с `LISTENING`.

### Проверка 3: CABINET_ENABLED включен?

```bash
# Проверить .env
type .env | findstr CABINET_ENABLED

# Должно быть: CABINET_ENABLED=true
```

### Проверка 4: Unified health endpoint отвечает?

```bash
# Попробуйте unified health endpoint (без токена)
curl http://localhost:8081/health/unified

# Должен вернуть JSON с информацией о системе
```

**Примечание**: Endpoint `/api/health` требует API токен аутентификацию. Для проверки работоспособности используйте `/health/unified`.

### Проверка 5: Cabinet auth endpoints доступны?

### Проверка 5: Cabinet auth endpoints доступны?

```bash
# Попробуйте вызвать auth endpoint
curl http://localhost:8081/api/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"test@test.com\",\"password\":\"test\"}"

# Должен вернуть ошибку 400 или 401 (это нормально - пользователь не существует)
# НЕ должен вернуть 404 (endpoint not found)
```

### Проверка 6: Flutter использует правильный URL?

В Flutter app:
- Android эмулятор: `10.0.2.2:8081` ✅
- Физическое устройство: `192.168.x.x:8081` ✅
- `localhost:8081` ❌ (только для iOS simulator)

---

## 📱 Как запустить Flutter приложение правильно

### Вариант 1: Android Эмулятор (рекомендуется для разработки)

```bash
cd flutter_app/ulya_vpn

# Установить зависимости (первый раз)
flutter pub get

# Запустить на Android эмуляторе
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8081
```

### Вариант 2: Физическое устройство

```bash
cd flutter_app/ulya_vpn

# Узнать ваш IP
ipconfig

# Запустить (замените IP на ваш)
flutter run --dart-define=API_BASE_URL=http://192.168.1.100:8081
```

### Вариант 3: Изменить default URL в коде

Если не хотите каждый раз указывать `--dart-define`, измените файл:

**`flutter_app/ulya_vpn/lib/config/api_config.dart`**:

```dart
class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8081',  // Для Android эмулятора
    // defaultValue: 'http://192.168.1.100:8081',  // Для физического устройства
  );
  // ...
}
```

Затем просто:
```bash
flutter run
```

---

## 🎯 Полная процедура запуска

### 1. Backend

```bash
# Убедитесь что .env настроен правильно
type .env | findstr CABINET

# Должно быть:
# CABINET_ENABLED=true
# CABINET_EMAIL_AUTH_ENABLED=true
# WEB_API_ENABLED=true
# WEB_API_PORT=8081

# Запустить backend
python main.py

# Или через Docker
docker-compose -f docker-compose.local.yml up -d
```

### 2. Проверка

```bash
# Проверить что API работает
curl http://localhost:8081/health/unified
```

### 3. Flutter App

```bash
cd flutter_app/ulya_vpn
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8081
```

### 4. В приложении

- Нажмите "Sign Up" (Регистрация)
- Введите:
  - Email: `test@example.com`
  - Password: `password123`
  - First Name: `Test`
- Нажмите "Create Account"

Должна пройти регистрация!

---

## ⚠️ Частые ошибки

### Ошибка: "CORS policy error"

**Решение**: Добавьте в `.env`:
```env
CABINET_ALLOWED_ORIGINS=*
```

### Ошибка: "404 Not Found on /api/health"

**Причина**: Неправильный endpoint.

**Решение**: Используйте `/health/unified` для проверки работоспособности:
```bash
curl http://localhost:8081/health/unified
```

Endpoint `/api/health` требует API token аутентификацию и используется для административных целей.

---

### Ошибка: "404 Not Found on /api/auth/login"

**Решение**: Cabinet отключен. Включите:
```env
CABINET_ENABLED=true
CABINET_EMAIL_AUTH_ENABLED=true
```

### Ошибка: "Connection refused" на Android

**Решение**: Не используйте `localhost`. Используйте:
```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8081
```

### Ошибка: "Connection timeout"

**Решение**: 
1. Firewall блокирует порт 8081
2. Backend не слушает на `0.0.0.0` (только на `127.0.0.1`)

Проверьте `.env`:
```env
WEB_API_HOST=0.0.0.0  # НЕ 127.0.0.1
```

---

## 📋 Чек-лист готовности

Перед запуском Flutter приложения убедитесь:

- [ ] Backend запущен (`python main.py` или Docker)
- [ ] `CABINET_ENABLED=true` в `.env`
- [ ] `CABINET_EMAIL_AUTH_ENABLED=true` в `.env`
- [ ] `WEB_API_ENABLED=true` в `.env`
- [ ] `WEB_API_HOST=0.0.0.0` в `.env`
- [ ] `WEB_API_PORT=8081` в `.env`
- [ ] `CABINET_ALLOWED_ORIGINS=*` в `.env` (для dev)
- [ ] Health endpoint отвечает: `curl http://localhost:8081/health/unified`
- [ ] Порт 8081 открыт: `netstat -an | findstr :8081`
- [ ] Flutter использует правильный URL (10.0.2.2 для Android эмулятора)
- [ ] PostgreSQL запущен и пользователь создан
- [ ] База данных remnawave_bot существует

---

## 🔐 Создание первого пользователя

Когда все настроено, можно зарегистрироваться через приложение:

1. Запустите Flutter app
2. Нажмите "Sign Up"
3. Заполните форму:
   - Email: любой email
   - Password: минимум 6 символов
   - First Name: ваше имя
4. Нажмите "Create Account"

Пользователь создастся в базе данных и вы автоматически войдете в систему!

---

## 📚 Дополнительная информация

- [FIX_API_404.md](FIX_API_404.md) - Исправление 404 ошибок на API endpoints
- [WINDOWS_SETUP.md](WINDOWS_SETUP.md) - Настройка PostgreSQL
- [FIX_USER_NOT_EXISTS.md](FIX_USER_NOT_EXISTS.md) - Исправление проблем с пользователем БД
- [API_ONLY_MODE.md](API_ONLY_MODE.md) - Настройка API-only режима
- [Flutter README](../flutter_app/ulya_vpn/README.md) - Документация Flutter приложения
