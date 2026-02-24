import '../../../../core/errors/failures.dart';
import '../entities/auth_tokens.dart';
import '../entities/user.dart';

/// Abstract repository — defines auth contracts used by use-cases.
abstract class AuthRepository {
  /// Register a new account with [email] and [password].
  ///
  /// Returns a [RegisterResult] indicating whether email verification is
  /// required, or throws a [Failure].
  Future<RegisterResult> registerWithEmail({
    required String email,
    required String password,
    String? firstName,
    String language = 'ru',
  });

  /// Authenticate with [email] and [password].
  ///
  /// Persists tokens to secure storage on success.
  Future<AuthTokens> loginWithEmail({
    required String email,
    required String password,
  });

  /// Attempt a silent token refresh using the stored refresh token.
  Future<AuthTokens> refreshToken();

  /// Remove stored tokens (effectively logs the user out).
  Future<void> logout();

  /// Returns the currently-stored access token, or `null`.
  Future<String?> getAccessToken();

  /// Returns the authenticated user profile.
  Future<User> getProfile();
}

/// Result returned by [AuthRepository.registerWithEmail].
class RegisterResult {
  const RegisterResult({
    required this.email,
    required this.requiresVerification,
    required this.message,
  });

  final String email;
  final bool requiresVerification;
  final String message;
}
