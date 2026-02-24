import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:ulya_vpn/core/errors/failures.dart';
import 'package:ulya_vpn/features/auth/domain/entities/auth_tokens.dart';
import 'package:ulya_vpn/features/auth/domain/entities/user.dart';
import 'package:ulya_vpn/features/auth/domain/repositories/auth_repository.dart';
import 'package:ulya_vpn/features/auth/domain/usecases/login_usecase.dart';
import 'package:ulya_vpn/features/auth/domain/usecases/register_usecase.dart';
import 'package:ulya_vpn/features/auth/presentation/bloc/auth_bloc.dart';
import 'package:ulya_vpn/features/auth/presentation/bloc/auth_event.dart';
import 'package:ulya_vpn/features/auth/presentation/bloc/auth_state.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockLoginUseCase extends Mock implements LoginUseCase {}

class MockRegisterUseCase extends Mock implements RegisterUseCase {}

class MockAuthRepository extends Mock implements AuthRepository {}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

final _testUser = User(
  id: 1,
  email: 'test@example.com',
  createdAt: DateTime(2024),
);

final _testTokens = AuthTokens(
  accessToken: 'access',
  refreshToken: 'refresh',
  expiresIn: 900,
  user: _testUser,
);

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

    registerFallbackValue(const LoginSubmitted(email: '', password: ''));
    registerFallbackValue(
      const RegisterSubmitted(email: '', password: ''),
    );
  });

  AuthBloc _bloc() => AuthBloc(
        loginUseCase: mockLogin,
        registerUseCase: mockRegister,
        authRepository: mockRepo,
      );

  group('AuthBloc — LoginSubmitted', () {
    blocTest<AuthBloc, AuthState>(
      'emits [AuthLoading, AuthLoginSuccess] on successful login',
      build: _bloc,
      setUp: () {
        when(
          () => mockLogin(
            email: any(named: 'email'),
            password: any(named: 'password'),
          ),
        ).thenAnswer((_) async => _testTokens);
      },
      act: (bloc) => bloc.add(
        const LoginSubmitted(email: 'test@example.com', password: 'secret123'),
      ),
      expect: () => [
        const AuthLoading(),
        AuthLoginSuccess(_testTokens),
      ],
    );

    blocTest<AuthBloc, AuthState>(
      'emits [AuthLoading, AuthError] on AuthFailure',
      build: _bloc,
      setUp: () {
        when(
          () => mockLogin(
            email: any(named: 'email'),
            password: any(named: 'password'),
          ),
        ).thenThrow(const AuthFailure());
      },
      act: (bloc) => bloc.add(
        const LoginSubmitted(email: 'bad@example.com', password: 'wrongpass'),
      ),
      expect: () => [
        const AuthLoading(),
        const AuthError('Неверный email или пароль'),
      ],
    );

    blocTest<AuthBloc, AuthState>(
      'emits [AuthLoading, AuthError] on NetworkFailure',
      build: _bloc,
      setUp: () {
        when(
          () => mockLogin(
            email: any(named: 'email'),
            password: any(named: 'password'),
          ),
        ).thenThrow(const NetworkFailure());
      },
      act: (bloc) => bloc.add(
        const LoginSubmitted(email: 'test@example.com', password: 'pass'),
      ),
      expect: () => [
        const AuthLoading(),
        const AuthError('Нет подключения к интернету'),
      ],
    );
  });

  group('AuthBloc — RegisterSubmitted', () {
    blocTest<AuthBloc, AuthState>(
      'emits [AuthLoading, AuthRegisterSuccess] when verification required',
      build: _bloc,
      setUp: () {
        when(
          () => mockRegister(
            email: any(named: 'email'),
            password: any(named: 'password'),
            firstName: any(named: 'firstName'),
            language: any(named: 'language'),
          ),
        ).thenAnswer(
          (_) async => const RegisterResult(
            email: 'new@example.com',
            requiresVerification: true,
            message: 'Письмо отправлено',
          ),
        );
      },
      act: (bloc) => bloc.add(
        const RegisterSubmitted(
          email: 'new@example.com',
          password: 'securePass1',
          firstName: 'Ulya',
        ),
      ),
      expect: () => [
        const AuthLoading(),
        const AuthRegisterSuccess(
          email: 'new@example.com',
          requiresVerification: true,
          message: 'Письмо отправлено',
        ),
      ],
    );

    blocTest<AuthBloc, AuthState>(
      'emits [AuthLoading, AuthError] when register fails',
      build: _bloc,
      setUp: () {
        when(
          () => mockRegister(
            email: any(named: 'email'),
            password: any(named: 'password'),
            firstName: any(named: 'firstName'),
            language: any(named: 'language'),
          ),
        ).thenThrow(const ServerFailure('Email уже занят', statusCode: 409));
      },
      act: (bloc) => bloc.add(
        const RegisterSubmitted(email: 'dup@example.com', password: 'pass1234'),
      ),
      expect: () => [
        const AuthLoading(),
        const AuthError('Email уже занят'),
      ],
    );
  });

  group('AuthBloc — LogoutRequested', () {
    blocTest<AuthBloc, AuthState>(
      'emits [AuthLoggedOut] after successful logout',
      build: _bloc,
      setUp: () {
        when(() => mockRepo.logout()).thenAnswer((_) async {});
      },
      act: (bloc) => bloc.add(const LogoutRequested()),
      expect: () => [const AuthLoggedOut()],
    );
  });
}
