# Ulya VPN

Ulya VPN - современное мобильное приложение для VPN сервиса.

## ⚠️ Важно: Настройка backend перед запуском

**Перед запуском Flutter приложения убедитесь что backend настроен правильно:**

1. **Включите Cabinet в `.env`**:
   ```env
   CABINET_ENABLED=true
   CABINET_EMAIL_AUTH_ENABLED=true
   WEB_API_ENABLED=true
   CABINET_ALLOWED_ORIGINS=*
   ```

2. **Перезапустите backend** после изменения `.env`

3. **Проверьте что API работает**: `curl http://localhost:8081/api/health`

**Подробная инструкция**: См. [../../docs/FLUTTER_CONNECTION.md](../../docs/FLUTTER_CONNECTION.md)

---

## Особенности

- ✨ Современный Material Design 3
- 🔐 Безопасная аутентификация
- 📱 Простой и интуитивный интерфейс
- 💳 Управление подписками
- 🌍 Поддержка нескольких серверов
- 📊 Статистика использования

## Требования

- Flutter SDK >= 3.0.0
- Dart SDK >= 3.0.0

## Установка

```bash
# Установите зависимости
flutter pub get

# Запустите приложение с правильным API URL
# Для Android эмулятора:
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8081

# Для физического устройства (замените на ваш IP):
flutter run --dart-define=API_BASE_URL=http://192.168.1.100:8081

# Для iOS simulator:
flutter run --dart-define=API_BASE_URL=http://localhost:8081
```

## ⚠️ Решение проблем

### Ошибка: "Connection refused"

**Причина**: Backend не настроен или Flutter использует неправильный URL.

**Решение**: См. подробную инструкцию [../../docs/FLUTTER_CONNECTION.md](../../docs/FLUTTER_CONNECTION.md)

Краткое решение:
1. Включите `CABINET_ENABLED=true` в backend `.env`
2. Перезапустите backend
3. Используйте `10.0.2.2` для Android эмулятора (не `localhost`)

---

## Конфигурация

Создайте файл `.env` в корне проекта со следующими переменными:

```env
API_BASE_URL=http://localhost:8080
```

## Структура проекта

```
lib/
├── main.dart                 # Точка входа приложения
├── config/                   # Конфигурация
│   ├── api_config.dart      # API конфигурация
│   └── theme_config.dart    # Тема приложения
├── models/                   # Модели данных
│   ├── user.dart
│   ├── subscription.dart
│   └── server.dart
├── services/                 # Сервисы
│   ├── api_service.dart
│   ├── auth_service.dart
│   └── storage_service.dart
├── providers/                # State management
│   ├── auth_provider.dart
│   └── subscription_provider.dart
├── screens/                  # Экраны приложения
│   ├── splash_screen.dart
│   ├── auth/
│   │   ├── login_screen.dart
│   │   └── register_screen.dart
│   ├── home/
│   │   └── home_screen.dart
│   ├── subscription/
│   │   └── subscription_screen.dart
│   └── profile/
│       └── profile_screen.dart
└── widgets/                  # Переиспользуемые виджеты
    ├── custom_button.dart
    └── custom_text_field.dart
```

## API Интеграция

Приложение подключается к backend API:

- **Авторизация**: `/api/auth/login`, `/api/auth/register`
- **Пользователи**: `/api/users/me`
- **Подписки**: `/api/subscriptions/`
- **Серверы**: `/api/servers/`

## Разработка

### Запуск на эмуляторе

```bash
flutter emulators --launch <emulator_id>
flutter run
```

### Запуск на устройстве

```bash
flutter devices
flutter run -d <device_id>
```

### Сборка Release

```bash
# Android
flutter build apk --release

# iOS
flutter build ios --release
```

## Лицензия

Proprietary
