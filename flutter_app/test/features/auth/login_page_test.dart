import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:ulya_vpn/core/errors/failures.dart';
import 'package:ulya_vpn/core/theme/app_theme.dart';
import 'package:ulya_vpn/features/auth/domain/entities/auth_tokens.dart';
import 'package:ulya_vpn/features/auth/domain/entities/user.dart';
import 'package:ulya_vpn/features/auth/domain/repositories/auth_repository.dart';
import 'package:ulya_vpn/features/auth/domain/usecases/login_usecase.dart';
import 'package:ulya_vpn/features/auth/domain/usecases/register_usecase.dart';
import 'package:ulya_vpn/features/auth/presentation/bloc/auth_bloc.dart';
import 'package:ulya_vpn/features/auth/presentation/pages/login_page.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockLoginUseCase extends Mock implements LoginUseCase {}

class MockRegisterUseCase extends Mock implements RegisterUseCase {}

class MockAuthRepository extends Mock implements AuthRepository {}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

final _tUser = User(id: 1, email: 'a@b.com', createdAt: DateTime(2024));
final _tTokens = AuthTokens(
  accessToken: 'tok',
  refreshToken: 'ref',
  expiresIn: 900,
  user: _tUser,
);

Widget _buildUnderTest({
  required AuthBloc bloc,
  VoidCallback? onGoToRegister,
  void Function(String)? onLoginSuccess,
}) {
  return MaterialApp(
    theme: AppTheme.dark,
    home: BlocProvider.value(
      value: bloc,
      child: LoginPage(
        onLoginSuccess: onLoginSuccess,
        onGoToRegister: onGoToRegister,
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockLoginUseCase mockLogin;
  late MockRegisterUseCase mockRegister;
  late MockAuthRepository mockRepo;

  setUp(() {
    mockLogin = MockLoginUseCase();
    mockRegister = MockRegisterUseCase();
    mockRepo = MockAuthRepository();
  });

  AuthBloc _bloc() => AuthBloc(
        loginUseCase: mockLogin,
        registerUseCase: mockRegister,
        authRepository: mockRepo,
      );

  testWidgets('renders email and password fields', (tester) async {
    await tester.pumpWidget(_buildUnderTest(bloc: _bloc()));

    expect(find.text('Email'), findsOneWidget);
    expect(find.text('Пароль'), findsOneWidget);
    expect(find.text('Войти'), findsAtLeastNWidgets(1));
  });

  testWidgets('shows validation errors when fields are empty', (tester) async {
    await tester.pumpWidget(_buildUnderTest(bloc: _bloc()));

    // Tap the login button without filling anything in.
    await tester.tap(find.text('Войти').last);
    await tester.pump();

    expect(find.text('Введите email'), findsOneWidget);
    expect(find.text('Введите пароль'), findsOneWidget);
  });

  testWidgets('shows invalid email error for bad format', (tester) async {
    await tester.pumpWidget(_buildUnderTest(bloc: _bloc()));

    await tester.enterText(
      find.widgetWithText(TextField, 'Email'),
      'notanemail',
    );
    await tester.tap(find.text('Войти').last);
    await tester.pump();

    expect(find.text('Неверный формат email'), findsOneWidget);
  });

  testWidgets('shows loading indicator while request is in flight',
      (tester) async {
    when(
      () => mockLogin(
        email: any(named: 'email'),
        password: any(named: 'password'),
      ),
    ).thenAnswer((_) async {
      await Future<void>.delayed(const Duration(seconds: 5));
      return _tTokens;
    });

    await tester.pumpWidget(_buildUnderTest(bloc: _bloc()));

    await tester.enterText(
      find.widgetWithText(TextField, 'Email'),
      'test@example.com',
    );
    await tester.enterText(
      find.widgetWithText(TextField, 'Пароль'),
      'password123',
    );
    await tester.tap(find.text('Войти').last);
    await tester.pump(); // trigger bloc event

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('calls onLoginSuccess callback on successful login',
      (tester) async {
    String? capturedToken;

    when(
      () => mockLogin(
        email: any(named: 'email'),
        password: any(named: 'password'),
      ),
    ).thenAnswer((_) async => _tTokens);

    await tester.pumpWidget(
      _buildUnderTest(
        bloc: _bloc(),
        onLoginSuccess: (token) => capturedToken = token,
      ),
    );

    await tester.enterText(
      find.widgetWithText(TextField, 'Email'),
      'test@example.com',
    );
    await tester.enterText(
      find.widgetWithText(TextField, 'Пароль'),
      'password123',
    );
    await tester.tap(find.text('Войти').last);
    await tester.pumpAndSettle();

    expect(capturedToken, 'tok');
  });

  testWidgets('shows snackbar on auth error', (tester) async {
    when(
      () => mockLogin(
        email: any(named: 'email'),
        password: any(named: 'password'),
      ),
    ).thenThrow(const AuthFailure());

    await tester.pumpWidget(_buildUnderTest(bloc: _bloc()));

    await tester.enterText(
      find.widgetWithText(TextField, 'Email'),
      'bad@example.com',
    );
    await tester.enterText(
      find.widgetWithText(TextField, 'Пароль'),
      'wrongpassword',
    );
    await tester.tap(find.text('Войти').last);
    await tester.pumpAndSettle();

    expect(find.text('Неверный email или пароль'), findsOneWidget);
  });

  testWidgets('calls onGoToRegister when register link is tapped',
      (tester) async {
    var called = false;
    await tester.pumpWidget(
      _buildUnderTest(bloc: _bloc(), onGoToRegister: () => called = true),
    );

    await tester.tap(find.text('Зарегистрироваться'));
    await tester.pump();

    expect(called, isTrue);
  });
}
