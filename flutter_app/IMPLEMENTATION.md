# Ulya VPN - Flutter Mobile Application

## Обзор проекта

Проект включает в себя:
1. **Backend** - Python/FastAPI сервер с поддержкой API-only режима (без Telegram бота)
2. **Flutter приложение** - Кроссплатформенное мобильное приложение для iOS и Android

## Что было реализовано

### 1. Backend - API-only режим

#### Изменения в коде

**app/config.py**:
- Добавлена настройка `TELEGRAM_BOT_ENABLED: bool = True`
- `BOT_TOKEN` сделан опциональным (`str | None`)

**main.py**:
- Инициализация бота пропускается если `TELEGRAM_BOT_ENABLED=false`
- Все сервисы, зависящие от бота, также пропускаются
- Web API запускается независимо от статуса бота

**.env.example**:
- Добавлены комментарии о новом режиме
- Инструкции по использованию API-only режима

### 2. Flutter MVP приложение

#### Структура проекта

```
flutter_app/ulya_vpn/
├── lib/
│   ├── config/
│   │   ├── api_config.dart       # API endpoints и настройки
│   │   └── theme_config.dart     # Темы оформления
│   ├── models/
│   │   ├── user.dart             # Модель пользователя
│   │   ├── subscription.dart     # Модель подписки
│   │   └── server.dart           # Модель VPN сервера
│   ├── services/
│   │   ├── api_service.dart      # HTTP клиент
│   │   ├── auth_service.dart     # Аутентификация
│   │   └── storage_service.dart  # Локальное хранилище
│   ├── providers/
│   │   ├── auth_provider.dart    # State для авторизации
│   │   └── subscription_provider.dart  # State для подписки
│   ├── screens/
│   │   ├── splash/
│   │   │   └── splash_screen.dart
│   │   ├── auth/
│   │   │   ├── login_screen.dart
│   │   │   └── register_screen.dart
│   │   ├── home/
│   │   │   └── home_screen.dart
│   │   ├── subscription/
│   │   │   └── subscription_screen.dart
│   │   └── profile/
│   │       └── profile_screen.dart
│   └── main.dart
├── assets/
│   ├── images/
│   └── icons/
├── pubspec.yaml
├── analysis_options.yaml
└── README.md
```

#### Основные функции

**Аутентификация**:
- Регистрация с email/password
- Вход с email/password
- Хранение токенов в защищенном хранилище
- Автоматический refresh токенов
- Logout с очисткой данных

**Управление подпиской**:
- Просмотр статуса подписки
- Отображение оставшихся дней
- Мониторинг использования трафика
- Информация об устройствах
- Индикация триального периода

**VPN подключение**:
- Визуальный индикатор статуса (Connected/Disconnected)
- Кнопка подключения/отключения
- Проверка активной подписки перед подключением

**Профиль**:
- Отображение информации пользователя
- Баланс аккаунта
- Настройки языка
- Информация о приложении
- Logout

#### Технологии

- **Flutter SDK**: ^3.0.0
- **State Management**: Provider
- **HTTP Client**: http, dio (prepared)
- **Local Storage**: shared_preferences, flutter_secure_storage
- **UI**: Material Design 3, Google Fonts
- **Utils**: intl, url_launcher

## Запуск проекта

### Backend

#### Вариант 1: Docker Compose (Рекомендуется)

```bash
# 1. Создайте .env файл
cp .env.example .env

# 2. Отредактируйте .env
nano .env
# Установите: TELEGRAM_BOT_ENABLED=false
# Установите: WEB_API_ENABLED=true

# 3. Запустите
docker-compose up -d

# 4. Проверьте
curl http://localhost:8080/api/health
```

#### Вариант 2: Локальная разработка

```bash
# 1. Установите зависимости
pip install -r requirements.txt

# 2. Настройте .env
TELEGRAM_BOT_ENABLED=false
WEB_API_ENABLED=true
DATABASE_MODE=postgres
# ... остальные настройки

# 3. Запустите PostgreSQL и Redis (через Docker или локально)
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:15
docker run -d -p 6379:6379 redis:7-alpine

# 4. Запустите миграции
alembic upgrade head

# 5. Запустите backend
python main.py
```

### Flutter приложение

```bash
# 1. Перейдите в директорию приложения
cd flutter_app/ulya_vpn

# 2. Установите зависимости
flutter pub get

# 3. Проверьте доступные устройства
flutter devices

# 4. Запустите приложение с указанием API URL
flutter run --dart-define=API_BASE_URL=http://YOUR_IP:8080

# Для Android эмулятора используйте 10.0.2.2
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8080

# Для физического устройства используйте IP вашего компьютера
flutter run --dart-define=API_BASE_URL=http://192.168.1.100:8080
```

## API Endpoints

Backend предоставляет следующие endpoints для мобильного приложения:

### Authentication

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "first_name": "John",
  "last_name": "Doe"
}

Response: 200 OK
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": { ... }
}
```

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

Response: 200 OK
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": { ... }
}
```

### Users

```http
GET /api/users/me
Authorization: Bearer ACCESS_TOKEN

Response: 200 OK
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "balance_kopeks": 100000,
  "balance_rubles": 1000.00,
  ...
}
```

### Subscriptions

```http
GET /api/users/me/subscription
Authorization: Bearer ACCESS_TOKEN

Response: 200 OK
{
  "id": 1,
  "status": "active",
  "is_trial": false,
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-02-01T00:00:00Z",
  "traffic_limit_gb": 100,
  "traffic_used_gb": 25.5,
  "device_limit": 2,
  ...
}
```

## Тестирование

### 1. Создание тестового пользователя

```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### 2. Вход в приложении

1. Запустите Flutter приложение
2. На экране Login введите:
   - Email: test@example.com
   - Password: password123
3. Нажмите "Sign In"

### 3. Проверка функционала

- **Home Screen**: Должен показать статус подписки (если есть)
- **Profile**: Должен показать данные пользователя
- **Subscription**: Детальная информация о подписке

## Дизайн приложения

### Цветовая схема

- **Primary**: Blue (#2196F3)
- **Secondary**: Light Blue (#03A9F4)
- **Accent**: Cyan (#00BCD4)
- **Success**: Green (#66BB6A)
- **Error**: Red (#E57373)

### Экраны

1. **Splash Screen**
   - Gradient background
   - Logo placeholder (круглая иконка)
   - Название "Ulya VPN"
   - Слоган "Secure. Fast. Private."
   - Loading indicator

2. **Login Screen**
   - Email и Password поля
   - Валидация полей
   - Кнопка "Sign In"
   - Ссылка на регистрацию

3. **Register Screen**
   - First Name, Last Name, Email, Password, Confirm Password
   - Валидация всех полей
   - Проверка совпадения паролей
   - Кнопка "Create Account"

4. **Home Screen**
   - Большая круглая кнопка с иконкой щита (подключение)
   - Статус: Connected / Disconnected
   - Карточка с информацией о подписке
   - Pull-to-refresh

5. **Subscription Screen**
   - Статус подписки (Active/Inactive)
   - Badge для Trial period
   - Даты начала и окончания
   - Оставшиеся дни
   - Использование трафика с прогресс-баром
   - Лимит устройств
   - Autopay статус

6. **Profile Screen**
   - Аватар с первой буквой имени
   - Имя и email
   - Баланс
   - Настройки (язык, уведомления, поддержка)
   - О приложении
   - Кнопка Logout

## Следующие шаги

### Обязательные (для production)

1. **Backend**:
   - [ ] Добавить полноценные API endpoints для регистрации/логина через email
   - [ ] Настроить SMTP для email верификации
   - [ ] Добавить rate limiting
   - [ ] Настроить CORS правильно
   - [ ] SSL/TLS сертификаты

2. **Flutter**:
   - [ ] Добавить реальную VPN интеграцию (OpenVPN/WireGuard)
   - [ ] Заменить placeholder логотипом Ulya VPN
   - [ ] Добавить обработку ошибок сети
   - [ ] Добавить offline режим
   - [ ] Реализовать payment flow

3. **Безопасность**:
   - [ ] Certificate pinning
   - [ ] Encryption at rest
   - [ ] Биометрическая аутентификация
   - [ ] Root/Jailbreak detection

### Опциональные (улучшения)

1. **Функциональность**:
   - [ ] Выбор сервера
   - [ ] Статистика использования
   - [ ] История подключений
   - [ ] Поддержка нескольких профилей
   - [ ] Split tunneling

2. **UX/UI**:
   - [ ] Анимации переходов
   - [ ] Onboarding flow
   - [ ] Haptic feedback
   - [ ] Dark mode toggle
   - [ ] Кастомизация темы

3. **Локализация**:
   - [ ] Русский язык
   - [ ] Английский язык
   - [ ] Автоопределение языка

4. **Аналитика**:
   - [ ] Firebase Analytics
   - [ ] Crash reporting
   - [ ] User behavior tracking

## Известные ограничения

1. **VPN подключение**: В текущей версии это mock - кнопка меняет статус, но реального VPN подключения нет
2. **Платежи**: Нет интеграции платежной системы в приложении
3. **Push уведомления**: Не реализованы
4. **Email верификация**: Требует настройки SMTP на backend
5. **Локализация**: Только английский интерфейс

## Поддержка

При возникновении проблем:

1. **Backend не запускается**:
   - Проверьте логи: `docker-compose logs -f`
   - Убедитесь что порты 8080, 5432, 6379 свободны
   - Проверьте .env конфигурацию

2. **Flutter приложение не подключается к API**:
   - Проверьте API_BASE_URL
   - Используйте IP вместо localhost для физических устройств
   - Для Android эмулятора: 10.0.2.2
   - Проверьте firewall

3. **Ошибки аутентификации**:
   - Убедитесь что backend запущен
   - Проверьте что пользователь создан в БД
   - Проверьте логи backend

## Лицензия

Proprietary - Все права защищены
