import '../../../../core/errors/failures.dart';
import '../../../../core/storage/secure_storage_service.dart';
import '../../domain/entities/auth_tokens.dart';
import '../../domain/entities/user.dart';
import '../../domain/repositories/auth_repository.dart';
import '../datasources/auth_remote_datasource.dart';

/// Concrete implementation of [AuthRepository].
class AuthRepositoryImpl implements AuthRepository {
  const AuthRepositoryImpl({
    required AuthRemoteDataSource remoteDataSource,
    required SecureStorageService storage,
  })  : _remote = remoteDataSource,
        _storage = storage;

  final AuthRemoteDataSource _remote;
  final SecureStorageService _storage;

  @override
  Future<RegisterResult> registerWithEmail({
    required String email,
    required String password,
    String? firstName,
    String language = 'ru',
  }) async {
    final data = await _remote.registerWithEmail(
      email: email,
      password: password,
      firstName: firstName,
      language: language,
    );
    return RegisterResult(
      email: data['email'] as String? ?? email,
      requiresVerification: (data['requires_verification'] as bool?) ?? true,
      message: data['message'] as String? ?? '',
    );
  }

  @override
  Future<AuthTokens> loginWithEmail({
    required String email,
    required String password,
  }) =>
      _remote.loginWithEmail(email: email, password: password);

  @override
  Future<AuthTokens> refreshToken() async {
    final storedToken = await _storage.readRefreshToken();
    if (storedToken == null) {
      throw const TokenExpiredFailure();
    }
    return _remote.refreshToken(storedToken);
  }

  @override
  Future<void> logout() => _storage.clearTokens();

  @override
  Future<String?> getAccessToken() => _storage.readAccessToken();

  @override
  Future<User> getProfile() => _remote.getProfile();
}
