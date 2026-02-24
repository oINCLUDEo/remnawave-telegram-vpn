import '../entities/auth_tokens.dart';
import '../repositories/auth_repository.dart';

/// Authenticates a user with email + password and persists tokens.
class LoginUseCase {
  const LoginUseCase(this._repository);

  final AuthRepository _repository;

  Future<AuthTokens> call({
    required String email,
    required String password,
  }) =>
      _repository.loginWithEmail(email: email, password: password);
}
