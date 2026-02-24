/// Base failure class for the domain layer.
///
/// Extends [Exception] so it can be caught with standard Dart try/on patterns.
abstract class Failure implements Exception {
  const Failure(this.message);
  final String message;

  @override
  String toString() => '$runtimeType: $message';
}

/// Network / HTTP-level failures.
class NetworkFailure extends Failure {
  const NetworkFailure([super.message = 'Нет подключения к интернету']);
}

/// Server returned an error response (4xx / 5xx).
class ServerFailure extends Failure {
  const ServerFailure(super.message, {this.statusCode});
  final int? statusCode;
}

/// Credentials are wrong (401 during login).
class AuthFailure extends Failure {
  const AuthFailure([super.message = 'Неверный email или пароль']);
}

/// The token has expired and could not be refreshed.
class TokenExpiredFailure extends Failure {
  const TokenExpiredFailure() : super('Сессия истекла. Войдите снова.');
}

/// Cache / local-storage failures.
class CacheFailure extends Failure {
  const CacheFailure([super.message = 'Ошибка локального хранилища']);
}

/// Validation failures (client-side).
class ValidationFailure extends Failure {
  const ValidationFailure(super.message);
}
