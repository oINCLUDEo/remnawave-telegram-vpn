# Ulya VPN — Flutter Mobile App

A modern, minimal VPN client application for the **Ulya VPN** service, built with Flutter.
It communicates exclusively with the existing Python/FastAPI backend via REST API — no Telegram dependency.

---

## Architecture

The project follows **Clean Architecture** with a feature-based folder structure:

```
lib/
├── core/
│   ├── constants/        # AppConstants (base URL, storage keys, etc.)
│   ├── di/               # GetIt dependency injection setup
│   ├── errors/           # Failure types (domain layer)
│   ├── network/          # Dio ApiClient + auto token refresh interceptor
│   ├── router/           # go_router navigation
│   ├── storage/          # SecureStorageService (JWT tokens)
│   └── theme/            # AppTheme (dark, minimalist) + AppColors
│
└── features/
    └── auth/
        ├── data/
        │   ├── datasources/   # AuthRemoteDataSource — raw HTTP calls
        │   ├── models/        # JSON ↔ Entity mappers
        │   └── repositories/  # AuthRepositoryImpl
        ├── domain/
        │   ├── entities/      # User, AuthTokens
        │   ├── repositories/  # AuthRepository (abstract)
        │   └── usecases/      # LoginUseCase, RegisterUseCase
        └── presentation/
            ├── bloc/          # AuthBloc, AuthEvent, AuthState
            ├── pages/         # LoginPage, RegisterPage
            └── widgets/       # AuthTextField, AuthButton
```

### State management
`flutter_bloc` (BLoC pattern) — predictable, testable, scalable.

### Authentication
JWT access + refresh tokens via `flutter_secure_storage`.
The `ApiClient` (Dio) automatically refreshes the access token on 401 responses.

---

## Getting started

### Prerequisites

| Tool    | Version |
|---------|---------|
| Flutter | ≥ 3.22  |
| Dart    | ≥ 3.3   |

### Install & run

```bash
cd flutter_app
flutter pub get
flutter run
```

### Configure backend URL

By default the app points to `http://localhost:8000`.
Override it in `lib/core/constants/app_constants.dart`:

```dart
static const String defaultBaseUrl = 'https://your-api-domain.com';
```

Or pass it via `setupDependencies(baseUrl: '...')` in `main.dart`.

---

## Running tests

```bash
cd flutter_app
flutter test
```

---

## In-App VPN Connection (flutter_v2ray)

The app routes traffic through the device's VPN API directly — no external app is needed.  
It uses the [`flutter_v2ray`](https://pub.dev/packages/flutter_v2ray) package which bundles the **Xray core** and supports VLESS, VMess, Trojan, Shadowsocks, and other protocols compatible with Remnawave/Xray panels.

### Connection flow

1. User taps **Connect**
2. `VpnCubit.connect()` calls `GET /mobile/v1/profile` to get the subscription URL
3. `FlutterV2ray.parseUrl(subscriptionUrl)` fetches the Remnawave subscription endpoint and parses all available proxy configs
4. `flutterV2ray.startV2Ray(config)` hands the config to the Xray core and starts the VPN tunnel via the platform VPN API
5. Speed/status updates are streamed via `onStatusChanged` callback

### Required native platform configuration

After running `flutter create` / when native directories exist, add the following:

#### Android — `android/app/src/main/AndroidManifest.xml`

Add inside `<manifest>` (before `<application>`):

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" />
```

Add inside `<application>`:

```xml
<service
    android:name="com.github.blueboytm.flutter_v2ray.v2ray.services.V2RayVpnService"
    android:permission="android.permission.BIND_VPN_SERVICE"
    android:exported="true"
    android:foregroundServiceType="specialUse">
    <intent-filter>
        <action android:name="android.net.VpnService" />
    </intent-filter>
    <property
        android:name="android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE"
        android:value="VPN" />
</service>
```

#### iOS — `ios/Runner/Info.plist`

```xml
<key>NSLocalNetworkUsageDescription</key>
<string>Используется для VPN-туннелирования трафика</string>
```

iOS also requires a **Network Extension target** in Xcode for full tunnel support.  
Follow the [flutter_v2ray iOS setup guide](https://pub.dev/packages/flutter_v2ray#ios-setup).

---

## Roadmap

- [x] Login screen (hidden from user flow, kept for future auth)
- [x] Registration screen (hidden from user flow, kept for future auth)
- [x] Home screen with VPN connect/disconnect button
- [x] Subscription management screen (Premium paywall)
- [x] Server selection screen (collapsible categories)
- [x] In-app VPN tunnel via flutter_v2ray + Xray core
- [x] Real traffic stats from /mobile/v1/profile
- [x] Real tariffs from /mobile/v1/tariffs
- [x] Real server list from /mobile/v1/servers
- [ ] Server selection → connect to selected server
- [ ] Profile / account screen
- [ ] Payment integration (YooKassa / Telegram Stars)
- [ ] iOS Network Extension target setup
