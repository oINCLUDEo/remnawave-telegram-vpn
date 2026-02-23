# Flutter App Technical Documentation

## API Integration

### Base Configuration
- Dev: `http://localhost:8000/cabinet`
- Prod: Configure in `lib/core/api/api_config.dart`

### Authentication Flow
1. Login/Register → Get JWT tokens
2. Store in `flutter_secure_storage`
3. Auto-refresh on 401 response
4. Include `Bearer {token}` in all requests

### Endpoints Used

**Auth:**
- `POST /auth/login-email` - Login
- `POST /auth/register-email` - Register
- `POST /auth/refresh` - Refresh token
- `GET /auth/me` - Get user info

**Balance:**
- `GET /balance` - Get balance
- `GET /balance/transactions` - Transaction history
- `POST /balance/top-up` - Create payment

**Subscription:**
- `GET /subscription` - Current subscription
- `GET /subscription/tariffs` - Available tariffs
- `POST /subscription/purchase-tariff` - Buy subscription
- `POST /subscription/activate-trial` - Activate trial

**Referral:**
- `GET /referral/stats` - Referral statistics
- `GET /referral/referrals` - List referrals

## State Management

Using Provider pattern:
- `AuthProvider` - Auth state, login/logout
- `SubscriptionProvider` - Subscription data
- `BalanceProvider` - Balance and transactions

Each provider:
- Manages its state
- Calls API through `ApiClient`
- Notifies listeners on changes

## Navigation

GoRouter with auth redirect:
- Not authenticated → `/auth/login`
- Authenticated → `/` (home)
- Deep links: `vpnapp://payment/callback`

## Security

### Token Storage
- Access token: Secure storage
- Refresh token: Secure storage
- Auto-refresh on expiry

### API Security
- All requests over HTTPS (prod)
- JWT Bearer authentication
- Automatic token refresh

## Payment Flow

1. User enters amount
2. Call `POST /balance/top-up`
3. Get `confirmation_url`
4. Open external browser/WebView
5. User completes payment
6. Redirect to `vpnapp://payment/callback`
7. Refresh balance

## Build Configuration

### Android
- Min SDK: 21
- Target SDK: 34
- Package: `com.vpnservice.app`

### iOS
- Min version: 12.0
- Bundle ID: `com.vpnservice.app`

## Performance

- Images: Use `cached_network_image`
- Lists: Use `ListView.builder`
- Heavy operations: Use `compute()`
- State: Minimize rebuilds with `Consumer`

## Error Handling

```dart
try {
  await api.something();
} on DioException catch (e) {
  if (e.response?.statusCode == 401) {
    // Token refresh handled automatically
  } else {
    // Show error to user
  }
}
```

## Testing

```bash
flutter test                    # Unit tests
flutter test integration_test/  # Integration tests
```

## Deployment

### Android
```bash
# Generate keystore
keytool -genkey -v -keystore android/app/key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias key

# Configure android/key.properties
storePassword=<password>
keyPassword=<password>
keyAlias=key
storeFile=key.jks

# Build
flutter build appbundle --release
```

### iOS
```bash
# Xcode: Configure signing
# Build
flutter build ios --release
# Archive in Xcode
```

## Monitoring

Add to `main.dart`:
```dart
FlutterError.onError = (details) {
  // Send to Sentry/Firebase Crashlytics
};
```

## Environment Variables

```bash
# Dev
flutter run

# Staging
flutter run --dart-define=ENV=staging

# Prod
flutter run --release --dart-define=ENV=prod
```

## API Response Models

All responses from API are `Map<String, dynamic>`.
Convert to models if needed:

```dart
class User {
  final int id;
  final String email;
  
  User.fromJson(Map<String, dynamic> json)
    : id = json['id'],
      email = json['email'];
}
```

## Common Issues

**API connection failed:**
- Check backend is running
- Android: Use `10.0.2.2` for localhost
- iOS: Use `localhost`

**Token refresh loop:**
- Clear storage: `flutter_secure_storage.deleteAll()`
- Re-login

**QR code not showing:**
- Check `config_link` exists in subscription data
- Install `qr_flutter` dependency

## Code Style

- Use `flutter_lints`
- Prefer const constructors
- Single quotes for strings
- Max line length: 120

## Git Workflow

```bash
git checkout -b feature/name
# Make changes
flutter test
git add .
git commit -m "feat: description"
git push origin feature/name
```
