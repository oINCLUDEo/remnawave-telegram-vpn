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

## Roadmap

- [x] Login screen
- [x] Registration screen (with email verification flow)
- [ ] Email verification screen
- [ ] Dashboard / Home screen
- [ ] Subscription management screen
- [ ] Profile screen
- [ ] VPN connection control
- [ ] Payment integration (YooKassa / Telegram Stars)
