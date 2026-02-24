import '../repositories/auth_repository.dart';

/// Registers a new account with email + password.
class RegisterUseCase {
  const RegisterUseCase(this._repository);

  final AuthRepository _repository;

  Future<RegisterResult> call({
    required String email,
    required String password,
    String? firstName,
    String language = 'ru',
  }) =>
      _repository.registerWithEmail(
        email: email,
        password: password,
        firstName: firstName,
        language: language,
      );
}
