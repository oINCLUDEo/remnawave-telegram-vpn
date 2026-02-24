import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/errors/failures.dart';
import '../../domain/usecases/login_usecase.dart';
import '../../domain/usecases/register_usecase.dart';
import '../../domain/repositories/auth_repository.dart';
import 'auth_event.dart';
import 'auth_state.dart';

/// BLoC that coordinates login, registration and logout flows.
class AuthBloc extends Bloc<AuthEvent, AuthState> {
  AuthBloc({
    required LoginUseCase loginUseCase,
    required RegisterUseCase registerUseCase,
    required AuthRepository authRepository,
  })  : _login = loginUseCase,
        _register = registerUseCase,
        _authRepository = authRepository,
        super(const AuthInitial()) {
    on<LoginSubmitted>(_onLoginSubmitted);
    on<RegisterSubmitted>(_onRegisterSubmitted);
    on<LogoutRequested>(_onLogoutRequested);
  }

  final LoginUseCase _login;
  final RegisterUseCase _register;
  final AuthRepository _authRepository;

  Future<void> _onLoginSubmitted(
    LoginSubmitted event,
    Emitter<AuthState> emit,
  ) async {
    emit(const AuthLoading());
    try {
      final tokens = await _login(email: event.email, password: event.password);
      emit(AuthLoginSuccess(tokens));
    } on Failure catch (f) {
      emit(AuthError(f.message));
    } catch (_) {
      emit(const AuthError('Неизвестная ошибка'));
    }
  }

  Future<void> _onRegisterSubmitted(
    RegisterSubmitted event,
    Emitter<AuthState> emit,
  ) async {
    emit(const AuthLoading());
    try {
      final result = await _register(
        email: event.email,
        password: event.password,
        firstName: event.firstName,
      );
      emit(AuthRegisterSuccess(
        email: result.email,
        requiresVerification: result.requiresVerification,
        message: result.message,
      ));
    } on Failure catch (f) {
      emit(AuthError(f.message));
    } catch (_) {
      emit(const AuthError('Неизвестная ошибка'));
    }
  }

  Future<void> _onLogoutRequested(
    LogoutRequested event,
    Emitter<AuthState> emit,
  ) async {
    await _authRepository.logout();
    emit(const AuthLoggedOut());
  }
}
