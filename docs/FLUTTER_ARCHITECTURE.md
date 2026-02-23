# Flutter приложение - Архитектура и развертывание

## Обзор архитектуры

### Компоненты системы

```
┌─────────────────────────────────────────────────────────────┐
│                     Flutter Mobile App                      │
│                    (iOS / Android)                          │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   UI Layer   │  │ Business     │  │  Data Layer  │     │
│  │              │──│   Logic      │──│              │     │
│  │  • Screens   │  │  • BLoC/     │  │  • API       │     │
│  │  • Widgets   │  │    Provider  │  │    Client    │     │
│  │  • Themes    │  │  • State Mgmt│  │  • Models    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTPS / REST API
                         │ WebSocket
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   Backend API Server                        │
│                    (FastAPI / Python)                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Cabinet API (/cabinet)                   │  │
│  │  • Authentication     • Balance & Payments            │  │
│  │  • Subscriptions      • Referral System              │  │
│  │  • Support Tickets    • Notifications                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Telegram Bot (legacy)                    │  │
│  │  • Aiogram handlers                                   │  │
│  │  • Bot commands & menus                              │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────┬───────────────────────────┬────────────────────┘
             │                           │
             ↓                           ↓
┌────────────────────┐       ┌──────────────────────┐
│   PostgreSQL DB    │       │   Redis Cache        │
│                    │       │                      │
│  • Users           │       │  • Sessions          │
│  • Subscriptions   │       │  • Rate Limiting     │
│  • Transactions    │       │  • Cache             │
│  • Referrals       │       └──────────────────────┘
└────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────┐
│              External Services                               │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  RemnaWave   │  │   YooKassa   │  │   Telegram   │     │
│  │     API      │  │   (СБП +     │  │    Stars     │     │
│  │              │  │    Cards)    │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Структура Flutter приложения

### Рекомендуемая структура проекта

```
vpn_app/
├── lib/
│   ├── main.dart
│   ├── app.dart
│   │
│   ├── core/
│   │   ├── constants/
│   │   │   ├── api_constants.dart
│   │   │   ├── app_constants.dart
│   │   │   └── route_constants.dart
│   │   │
│   │   ├── errors/
│   │   │   ├── exceptions.dart
│   │   │   └── failures.dart
│   │   │
│   │   ├── network/
│   │   │   ├── api_client.dart
│   │   │   ├── dio_client.dart
│   │   │   ├── interceptors.dart
│   │   │   └── network_info.dart
│   │   │
│   │   ├── storage/
│   │   │   ├── secure_storage.dart
│   │   │   └── local_storage.dart
│   │   │
│   │   └── utils/
│   │       ├── logger.dart
│   │       ├── validators.dart
│   │       └── formatters.dart
│   │
│   ├── features/
│   │   ├── auth/
│   │   │   ├── data/
│   │   │   │   ├── models/
│   │   │   │   │   ├── user_model.dart
│   │   │   │   │   └── auth_response_model.dart
│   │   │   │   ├── repositories/
│   │   │   │   │   └── auth_repository_impl.dart
│   │   │   │   └── datasources/
│   │   │   │       └── auth_remote_datasource.dart
│   │   │   │
│   │   │   ├── domain/
│   │   │   │   ├── entities/
│   │   │   │   │   └── user.dart
│   │   │   │   ├── repositories/
│   │   │   │   │   └── auth_repository.dart
│   │   │   │   └── usecases/
│   │   │   │       ├── login.dart
│   │   │   │       ├── register.dart
│   │   │   │       └── logout.dart
│   │   │   │
│   │   │   └── presentation/
│   │   │       ├── bloc/
│   │   │       │   ├── auth_bloc.dart
│   │   │       │   ├── auth_event.dart
│   │   │       │   └── auth_state.dart
│   │   │       ├── pages/
│   │   │       │   ├── login_page.dart
│   │   │       │   ├── register_page.dart
│   │   │       │   └── forgot_password_page.dart
│   │   │       └── widgets/
│   │   │           ├── login_form.dart
│   │   │           └── social_auth_buttons.dart
│   │   │
│   │   ├── subscription/
│   │   │   ├── data/
│   │   │   │   ├── models/
│   │   │   │   ├── repositories/
│   │   │   │   └── datasources/
│   │   │   ├── domain/
│   │   │   │   ├── entities/
│   │   │   │   ├── repositories/
│   │   │   │   └── usecases/
│   │   │   └── presentation/
│   │   │       ├── bloc/
│   │   │       ├── pages/
│   │   │       └── widgets/
│   │   │
│   │   ├── balance/
│   │   │   └── ... (аналогичная структура)
│   │   │
│   │   ├── referral/
│   │   │   └── ...
│   │   │
│   │   └── support/
│   │       └── ...
│   │
│   ├── shared/
│   │   ├── widgets/
│   │   │   ├── custom_button.dart
│   │   │   ├── custom_textfield.dart
│   │   │   ├── loading_indicator.dart
│   │   │   └── error_widget.dart
│   │   │
│   │   ├── theme/
│   │   │   ├── app_theme.dart
│   │   │   ├── app_colors.dart
│   │   │   └── app_text_styles.dart
│   │   │
│   │   └── extensions/
│   │       ├── context_extensions.dart
│   │       └── string_extensions.dart
│   │
│   └── l10n/
│       ├── app_en.arb
│       └── app_ru.arb
│
├── test/
│   ├── unit/
│   ├── widget/
│   └── integration/
│
├── android/
├── ios/
├── web/
│
├── pubspec.yaml
├── analysis_options.yaml
└── README.md
```

## Ключевые зависимости

### pubspec.yaml

```yaml
name: vpn_app
description: VPN Service Mobile Application
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  
  # State Management
  flutter_bloc: ^8.1.3
  equatable: ^2.0.5
  
  # Network
  dio: ^5.4.0
  retrofit: ^4.0.3
  pretty_dio_logger: ^1.3.1
  
  # Storage
  flutter_secure_storage: ^9.0.0
  shared_preferences: ^2.2.2
  hive: ^2.2.3
  hive_flutter: ^1.1.0
  
  # Navigation
  go_router: ^13.0.0
  
  # UI
  flutter_svg: ^2.0.9
  cached_network_image: ^3.3.0
  shimmer: ^3.0.0
  lottie: ^2.7.0
  
  # Utilities
  intl: ^0.19.0
  url_launcher: ^6.2.2
  uni_links: ^0.5.1
  package_info_plus: ^5.0.1
  connectivity_plus: ^5.0.2
  
  # QR Code
  qr_flutter: ^4.1.0
  mobile_scanner: ^3.5.5
  
  # WebSocket
  web_socket_channel: ^2.4.0
  
  # Localization
  flutter_localizations:
    sdk: flutter
  
  # Dependency Injection
  get_it: ^7.6.4
  injectable: ^2.3.2

dev_dependencies:
  flutter_test:
    sdk: flutter
  
  # Code Generation
  build_runner: ^2.4.7
  retrofit_generator: ^8.0.4
  json_serializable: ^6.7.1
  hive_generator: ^2.0.1
  injectable_generator: ^2.4.1
  
  # Testing
  mockito: ^5.4.4
  bloc_test: ^9.1.5
  
  # Linting
  flutter_lints: ^3.0.1

flutter:
  uses-material-design: true
  
  assets:
    - assets/images/
    - assets/icons/
    - assets/animations/
  
  fonts:
    - family: Roboto
      fonts:
        - asset: assets/fonts/Roboto-Regular.ttf
        - asset: assets/fonts/Roboto-Bold.ttf
          weight: 700
```

## Clean Architecture реализация

### 1. Data Layer

**models/user_model.dart:**
```dart
import 'package:json_annotation/json_annotation.dart';
import '../../domain/entities/user.dart';

part 'user_model.g.dart';

@JsonSerializable()
class UserModel extends User {
  const UserModel({
    required super.id,
    required super.email,
    super.telegramId,
    super.username,
    required super.firstName,
    super.lastName,
    required super.balanceRubles,
    required super.referralCode,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) => 
      _$UserModelFromJson(json);
  
  Map<String, dynamic> toJson() => _$UserModelToJson(this);
}
```

**repositories/auth_repository_impl.dart:**
```dart
import 'package:dartz/dartz.dart';
import '../../domain/entities/user.dart';
import '../../domain/repositories/auth_repository.dart';
import '../datasources/auth_remote_datasource.dart';
import '../../../../core/errors/failures.dart';
import '../../../../core/errors/exceptions.dart';

class AuthRepositoryImpl implements AuthRepository {
  final AuthRemoteDataSource remoteDataSource;
  
  AuthRepositoryImpl({required this.remoteDataSource});
  
  @override
  Future<Either<Failure, User>> login(String email, String password) async {
    try {
      final user = await remoteDataSource.login(email, password);
      return Right(user);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException {
      return Left(NetworkFailure());
    }
  }
  
  @override
  Future<Either<Failure, User>> register(String email, String password, String firstName) async {
    try {
      final user = await remoteDataSource.register(email, password, firstName);
      return Right(user);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    }
  }
}
```

### 2. Domain Layer

**entities/user.dart:**
```dart
import 'package:equatable/equatable.dart';

class User extends Equatable {
  final int id;
  final String email;
  final int? telegramId;
  final String? username;
  final String firstName;
  final String? lastName;
  final double balanceRubles;
  final String referralCode;

  const User({
    required this.id,
    required this.email,
    this.telegramId,
    this.username,
    required this.firstName,
    this.lastName,
    required this.balanceRubles,
    required this.referralCode,
  });

  @override
  List<Object?> get props => [
    id,
    email,
    telegramId,
    username,
    firstName,
    lastName,
    balanceRubles,
    referralCode,
  ];
}
```

**usecases/login.dart:**
```dart
import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../entities/user.dart';
import '../repositories/auth_repository.dart';

class Login {
  final AuthRepository repository;

  Login(this.repository);

  Future<Either<Failure, User>> call(String email, String password) async {
    return await repository.login(email, password);
  }
}
```

### 3. Presentation Layer (BLoC)

**bloc/auth_bloc.dart:**
```dart
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import '../../domain/usecases/login.dart';
import '../../domain/usecases/register.dart';
import '../../domain/entities/user.dart';

// Events
abstract class AuthEvent extends Equatable {
  @override
  List<Object?> get props => [];
}

class LoginRequested extends AuthEvent {
  final String email;
  final String password;

  LoginRequested(this.email, this.password);

  @override
  List<Object?> get props => [email, password];
}

class RegisterRequested extends AuthEvent {
  final String email;
  final String password;
  final String firstName;

  RegisterRequested(this.email, this.password, this.firstName);

  @override
  List<Object?> get props => [email, password, firstName];
}

class LogoutRequested extends AuthEvent {}

// States
abstract class AuthState extends Equatable {
  @override
  List<Object?> get props => [];
}

class AuthInitial extends AuthState {}

class AuthLoading extends AuthState {}

class Authenticated extends AuthState {
  final User user;

  Authenticated(this.user);

  @override
  List<Object?> get props => [user];
}

class Unauthenticated extends AuthState {}

class AuthError extends AuthState {
  final String message;

  AuthError(this.message);

  @override
  List<Object?> get props => [message];
}

// BLoC
class AuthBloc extends Bloc<AuthEvent, AuthState> {
  final Login loginUseCase;
  final Register registerUseCase;

  AuthBloc({
    required this.loginUseCase,
    required this.registerUseCase,
  }) : super(AuthInitial()) {
    on<LoginRequested>(_onLoginRequested);
    on<RegisterRequested>(_onRegisterRequested);
    on<LogoutRequested>(_onLogoutRequested);
  }

  Future<void> _onLoginRequested(
    LoginRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());
    
    final result = await loginUseCase(event.email, event.password);
    
    result.fold(
      (failure) => emit(AuthError(failure.message)),
      (user) => emit(Authenticated(user)),
    );
  }

  Future<void> _onRegisterRequested(
    RegisterRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());
    
    final result = await registerUseCase(event.email, event.password, event.firstName);
    
    result.fold(
      (failure) => emit(AuthError(failure.message)),
      (user) => emit(Authenticated(user)),
    );
  }

  Future<void> _onLogoutRequested(
    LogoutRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(Unauthenticated());
  }
}
```

## Dependency Injection

**core/di/injection.dart:**
```dart
import 'package:get_it/get_it.dart';
import 'package:dio/dio.dart';
import '../network/dio_client.dart';
import '../../features/auth/data/datasources/auth_remote_datasource.dart';
import '../../features/auth/data/repositories/auth_repository_impl.dart';
import '../../features/auth/domain/repositories/auth_repository.dart';
import '../../features/auth/domain/usecases/login.dart';
import '../../features/auth/domain/usecases/register.dart';
import '../../features/auth/presentation/bloc/auth_bloc.dart';

final getIt = GetIt.instance;

Future<void> setupDependencyInjection() async {
  // Core
  getIt.registerLazySingleton<Dio>(() => Dio());
  getIt.registerLazySingleton<DioClient>(() => DioClient(getIt()));
  
  // Auth
  getIt.registerLazySingleton<AuthRemoteDataSource>(
    () => AuthRemoteDataSourceImpl(dioClient: getIt()),
  );
  
  getIt.registerLazySingleton<AuthRepository>(
    () => AuthRepositoryImpl(remoteDataSource: getIt()),
  );
  
  getIt.registerLazySingleton(() => Login(getIt()));
  getIt.registerLazySingleton(() => Register(getIt()));
  
  getIt.registerFactory(
    () => AuthBloc(
      loginUseCase: getIt(),
      registerUseCase: getIt(),
    ),
  );
}
```

## Развертывание Backend для Flutter

### Docker Compose конфигурация

**docker-compose.flutter.yml:**
```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: vpn_api
    ports:
      - "8000:8000"
    environment:
      - CABINET_ENABLED=true
      - CABINET_JWT_SECRET=${CABINET_JWT_SECRET}
      - CABINET_ALLOWED_ORIGINS=${CABINET_ALLOWED_ORIGINS}
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/vpn_db
      - REDIS_HOST=redis
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
      - ./media:/app/media
    restart: unless-stopped
    networks:
      - vpn_network

  db:
    image: postgres:15-alpine
    container_name: vpn_db
    environment:
      - POSTGRES_DB=vpn_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - vpn_network

  redis:
    image: redis:7-alpine
    container_name: vpn_redis
    restart: unless-stopped
    networks:
      - vpn_network

  nginx:
    image: nginx:alpine
    container_name: vpn_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: unless-stopped
    networks:
      - vpn_network

volumes:
  postgres_data:

networks:
  vpn_network:
    driver: bridge
```

### Nginx конфигурация

**nginx.conf:**
```nginx
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        client_max_body_size 10M;

        location /cabinet {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /docs {
            proxy_pass http://api;
            proxy_set_header Host $host;
        }

        location /ws {
            proxy_pass http://api;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }

        location /media {
            alias /app/media;
        }
    }
}
```

## CI/CD Pipeline

### GitHub Actions

**.github/workflows/flutter-build.yml:**
```yaml
name: Flutter Build

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  build-android:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          distribution: 'zulu'
          java-version: '17'
      
      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.16.0'
          channel: 'stable'
      
      - name: Install dependencies
        run: flutter pub get
      
      - name: Run tests
        run: flutter test
      
      - name: Build APK
        run: flutter build apk --release
      
      - name: Upload APK
        uses: actions/upload-artifact@v3
        with:
          name: app-release.apk
          path: build/app/outputs/flutter-apk/app-release.apk

  build-ios:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.16.0'
          channel: 'stable'
      
      - name: Install dependencies
        run: flutter pub get
      
      - name: Build iOS
        run: flutter build ios --release --no-codesign
```

## Мониторинг и логирование

### Sentry Integration

```dart
import 'package:sentry_flutter/sentry_flutter.dart';

Future<void> main() async {
  await SentryFlutter.init(
    (options) {
      options.dsn = 'your-sentry-dsn';
      options.tracesSampleRate = 1.0;
    },
    appRunner: () => runApp(MyApp()),
  );
}
```

### Firebase Analytics

```dart
import 'package:firebase_analytics/firebase_analytics.dart';

class AnalyticsService {
  static final FirebaseAnalytics _analytics = FirebaseAnalytics.instance;
  
  static Future<void> logEvent(String name, Map<String, dynamic> parameters) async {
    await _analytics.logEvent(
      name: name,
      parameters: parameters,
    );
  }
  
  static Future<void> setUserId(String userId) async {
    await _analytics.setUserId(id: userId);
  }
}
```

## Безопасность

### SSL Pinning

```dart
import 'package:dio/dio.dart';
import 'package:dio/io.dart';

class ApiClient {
  static Dio createDio() {
    final dio = Dio();
    
    (dio.httpClientAdapter as IOHttpClientAdapter).onHttpClientCreate = (client) {
      client.badCertificateCallback = (cert, host, port) {
        // Проверяем SHA256 fingerprint сертификата
        final sha256 = cert.sha256.toString();
        return sha256 == 'YOUR_CERT_SHA256_HERE';
      };
      return client;
    };
    
    return dio;
  }
}
```

### Obfuscation

```bash
# Android
flutter build apk --obfuscate --split-debug-info=build/app/outputs/symbols

# iOS
flutter build ios --obfuscate --split-debug-info=build/ios/outputs/symbols
```

## Тестирование

### Unit Tests

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:bloc_test/bloc_test.dart';

void main() {
  group('AuthBloc', () {
    late AuthBloc authBloc;
    late MockLogin mockLogin;
    
    setUp(() {
      mockLogin = MockLogin();
      authBloc = AuthBloc(loginUseCase: mockLogin);
    });
    
    blocTest<AuthBloc, AuthState>(
      'emits [AuthLoading, Authenticated] when login succeeds',
      build: () {
        when(mockLogin('test@example.com', 'password'))
            .thenAnswer((_) async => Right(testUser));
        return authBloc;
      },
      act: (bloc) => bloc.add(LoginRequested('test@example.com', 'password')),
      expect: () => [
        AuthLoading(),
        Authenticated(testUser),
      ],
    );
  });
}
```

## Production Checklist

- [ ] SSL сертификаты настроены
- [ ] Все секретные ключи уникальны
- [ ] CORS origins настроены правильно
- [ ] Rate limiting включен
- [ ] Логирование настроено
- [ ] Мониторинг настроен (Sentry, etc)
- [ ] Бэкапы базы данных автоматизированы
- [ ] SSL Pinning реализован
- [ ] Обфускация кода включена
- [ ] App Store / Play Store метаданные готовы
- [ ] Privacy Policy и Terms of Service опубликованы
- [ ] Push notifications настроены (опционально)
- [ ] Deep links протестированы
- [ ] Платежные системы протестированы
- [ ] App signing настроен

## Поддержка

- GitHub Issues: https://github.com/oINCLUDEo/remnawave-telegram-vpn/issues
- Telegram чат: https://t.me/+wTdMtSWq8YdmZmVi
- Email: support@yourdomain.com
