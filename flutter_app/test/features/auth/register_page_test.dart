import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:ulya_vpn/core/theme/app_theme.dart';
import 'package:ulya_vpn/features/auth/domain/repositories/auth_repository.dart';
import 'package:ulya_vpn/features/auth/domain/usecases/login_usecase.dart';
import 'package:ulya_vpn/features/auth/domain/usecases/register_usecase.dart';
import 'package:ulya_vpn/features/auth/presentation/bloc/auth_bloc.dart';
import 'package:ulya_vpn/features/auth/presentation/pages/register_page.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockLoginUseCase extends Mock implements LoginUseCase {}

class MockRegisterUseCase extends Mock implements RegisterUseCase {}

class MockAuthRepository extends Mock implements AuthRepository {}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

Widget _buildUnderTest({
  required AuthBloc bloc,
  VoidCallback? onGoToLogin,
}) {
  return MaterialApp(
    theme: AppTheme.dark,
    home: BlocProvider.value(
      value: bloc,
      child: RegisterPage(onGoToLogin: onGoToLogin),
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

  testWidgets('renders all form fields', (tester) async {
    await tester.pumpWidget(_buildUnderTest(bloc: _bloc()));

    expect(find.text('Имя'), findsOneWidget);
    expect(find.text('Email'), findsOneWidget);
    expect(find.text('Пароль'), findsOneWidget);
    expect(find.text('Повторите пароль'), findsOneWidget);
    expect(find.text('Зарегистрироваться'), findsAtLeastNWidgets(1));
  });

  testWidgets('shows validation errors when submitted empty', (tester) async {
    await tester.pumpWidget(_buildUnderTest(bloc: _bloc()));

    await tester.tap(find.text('Зарегистрироваться').last);
    await tester.pump();

    expect(find.text('Введите имя'), findsOneWidget);
    expect(find.text('Введите email'), findsOneWidget);
    expect(find.text('Введите пароль'), findsOneWidget);
    expect(find.text('Необходимо принять условия'), findsOneWidget);
  });

  testWidgets('shows error when passwords do not match', (tester) async {
    await tester.pumpWidget(_buildUnderTest(bloc: _bloc()));

    await tester.enterText(find.widgetWithText(TextField, 'Имя'), 'Ulya');
    await tester.enterText(
        find.widgetWithText(TextField, 'Email'), 'u@example.com');
    await tester.enterText(
        find.widgetWithText(TextField, 'Пароль'), 'password1');
    await tester.enterText(
        find.widgetWithText(TextField, 'Повторите пароль'), 'password2');

    // Accept terms.
    await tester.tap(find.byType(Checkbox));
    await tester.pump();

    await tester.tap(find.text('Зарегистрироваться').last);
    await tester.pump();

    expect(find.text('Пароли не совпадают'), findsOneWidget);
  });

  testWidgets('shows short-password error', (tester) async {
    await tester.pumpWidget(_buildUnderTest(bloc: _bloc()));

    await tester.enterText(find.widgetWithText(TextField, 'Имя'), 'Ulya');
    await tester.enterText(
        find.widgetWithText(TextField, 'Email'), 'u@example.com');
    await tester.enterText(find.widgetWithText(TextField, 'Пароль'), 'short');
    await tester.enterText(
        find.widgetWithText(TextField, 'Повторите пароль'), 'short');

    await tester.tap(find.byType(Checkbox));
    await tester.pump();

    await tester.tap(find.text('Зарегистрироваться').last);
    await tester.pump();

    expect(find.textContaining('Минимум'), findsOneWidget);
  });

  testWidgets('dispatches RegisterSubmitted on valid form', (tester) async {
    when(
      () => mockRegister(
        email: any(named: 'email'),
        password: any(named: 'password'),
        firstName: any(named: 'firstName'),
        language: any(named: 'language'),
      ),
    ).thenAnswer(
      (_) async => const RegisterResult(
        email: 'u@example.com',
        requiresVerification: true,
        message: 'ok',
      ),
    );

    await tester.pumpWidget(_buildUnderTest(bloc: _bloc()));

    await tester.enterText(find.widgetWithText(TextField, 'Имя'), 'Ulya');
    await tester.enterText(
        find.widgetWithText(TextField, 'Email'), 'u@example.com');
    await tester.enterText(
        find.widgetWithText(TextField, 'Пароль'), 'securepw1');
    await tester.enterText(
        find.widgetWithText(TextField, 'Повторите пароль'), 'securepw1');

    await tester.tap(find.byType(Checkbox));
    await tester.pump();

    await tester.tap(find.text('Зарегистрироваться').last);
    await tester.pumpAndSettle();

    verify(
      () => mockRegister(
        email: 'u@example.com',
        password: 'securepw1',
        firstName: 'Ulya',
        language: any(named: 'language'),
      ),
    ).called(1);
  });

  testWidgets('calls onGoToLogin when back button is tapped', (tester) async {
    var called = false;
    await tester.pumpWidget(
      _buildUnderTest(bloc: _bloc(), onGoToLogin: () => called = true),
    );

    await tester.tap(find.byType(IconButton).first);
    await tester.pump();

    expect(called, isTrue);
  });
}
