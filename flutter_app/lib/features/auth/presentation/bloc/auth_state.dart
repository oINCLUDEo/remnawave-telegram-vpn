import 'package:equatable/equatable.dart';

import '../../domain/entities/auth_tokens.dart';

abstract class AuthState extends Equatable {
  const AuthState();

  @override
  List<Object?> get props => [];
}

/// Initial / idle state.
class AuthInitial extends AuthState {
  const AuthInitial();
}

/// A request is in flight.
class AuthLoading extends AuthState {
  const AuthLoading();
}

/// Login succeeded.
class AuthLoginSuccess extends AuthState {
  const AuthLoginSuccess(this.tokens);
  final AuthTokens tokens;

  @override
  List<Object?> get props => [tokens];
}

/// Registration succeeded (email verification may be required).
class AuthRegisterSuccess extends AuthState {
  const AuthRegisterSuccess({
    required this.email,
    required this.requiresVerification,
    required this.message,
  });

  final String email;
  final bool requiresVerification;
  final String message;

  @override
  List<Object?> get props => [email, requiresVerification, message];
}

/// The user has been logged out.
class AuthLoggedOut extends AuthState {
  const AuthLoggedOut();
}

/// An error occurred.
class AuthError extends AuthState {
  const AuthError(this.message);
  final String message;

  @override
  List<Object?> get props => [message];
}
