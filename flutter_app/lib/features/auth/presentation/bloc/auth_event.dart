import 'package:equatable/equatable.dart';

abstract class AuthEvent extends Equatable {
  const AuthEvent();

  @override
  List<Object?> get props => [];
}

class LoginSubmitted extends AuthEvent {
  const LoginSubmitted({required this.email, required this.password});

  final String email;
  final String password;

  @override
  List<Object?> get props => [email, password];
}

class RegisterSubmitted extends AuthEvent {
  const RegisterSubmitted({
    required this.email,
    required this.password,
    this.firstName,
  });

  final String email;
  final String password;
  final String? firstName;

  @override
  List<Object?> get props => [email, password, firstName];
}

class LogoutRequested extends AuthEvent {
  const LogoutRequested();
}
