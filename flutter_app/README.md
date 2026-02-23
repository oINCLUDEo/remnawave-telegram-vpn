# VPN Flutter App

Flutter приложение для VPN сервиса. Работает с API-only backend.

## Требования

- Flutter 3.0+
- API backend запущен на localhost:8000

## Установка

```bash
flutter pub get
```

## Запуск

```bash
# Development
flutter run

# Production
flutter run --release --dart-define=ENV=prod
```

## Сборка

### Android
```bash
flutter build apk --release
flutter build appbundle --release
```

### iOS
```bash
flutter build ios --release
```

## Конфигурация

API URL настраивается в `lib/core/api/api_config.dart`:
- dev: `http://localhost:8000/cabinet`
- prod: изменить в файле

## Структура

```
lib/
├── main.dart                 # Entry point
├── core/
│   ├── api/                  # API client, config
│   ├── providers/            # State management
│   ├── router/               # Navigation
│   └── theme/                # App theme
└── screens/
    ├── auth/                 # Login, register
    ├── home/                 # Main screen
    ├── balance/              # Balance, payments
    ├── subscription/         # VPN subscription
    ├── referral/             # Referral program
    └── profile/              # User profile
```

## Features

- ✅ Email authentication
- ✅ JWT auto-refresh
- ✅ Balance & payments (YooKassa)
- ✅ Subscription management
- ✅ VPN config QR codes
- ✅ Referral system
- ✅ Material 3 design

## Dependencies

Core:
- `provider` - State management
- `dio` - HTTP client
- `go_router` - Navigation
- `flutter_secure_storage` - Secure token storage

UI:
- `qr_flutter` - QR code generation
- `url_launcher` - External URLs

## Development

### Add new screen
1. Create in `lib/screens/feature_name/`
2. Add route in `lib/core/router/app_router.dart`
3. Add provider if needed

### API integration
All endpoints in `lib/core/api/api_client.dart`

## Testing

```bash
flutter test
```

## Production Setup

1. Change API URL in `api_config.dart`
2. Setup SSL pinning (recommended)
3. Configure deep links for payment callbacks
4. Add Firebase for push notifications (optional)
5. Setup Sentry for error tracking (optional)

## Deep Links

iOS: `vpnapp://`
Android: `vpnapp://`

Configure in:
- iOS: `ios/Runner/Info.plist`
- Android: `android/app/src/main/AndroidManifest.xml`

## Known Issues

None

## License

MIT
