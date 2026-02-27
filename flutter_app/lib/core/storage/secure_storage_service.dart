import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../constants/app_constants.dart';

/// Thin wrapper around [FlutterSecureStorage] scoped to auth tokens.
class SecureStorageService {
  const SecureStorageService(this._storage);

  final FlutterSecureStorage _storage;

  static const _options = AndroidOptions(
    encryptedSharedPreferences: true,
  );

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await Future.wait([
      _storage.write(
        key: AppConstants.accessTokenKey,
        value: accessToken,
        aOptions: _options,
      ),
      _storage.write(
        key: AppConstants.refreshTokenKey,
        value: refreshToken,
        aOptions: _options,
      ),
    ]);
  }

  /// Saves only the access token and clears any stored refresh token.
  ///
  /// Used for DEV-mode tokens issued by `/mobile/v1/dev/auth`, which are
  /// long-lived and do not support refresh.
  Future<void> saveAccessTokenOnly(String accessToken) async {
    await Future.wait([
      _storage.write(
        key: AppConstants.accessTokenKey,
        value: accessToken,
        aOptions: _options,
      ),
      _storage.delete(
        key: AppConstants.refreshTokenKey,
        aOptions: _options,
      ),
    ]);
  }

  Future<String?> readAccessToken() =>
      _storage.read(key: AppConstants.accessTokenKey, aOptions: _options);

  Future<String?> readRefreshToken() =>
      _storage.read(key: AppConstants.refreshTokenKey, aOptions: _options);

  Future<void> clearTokens() async {
    await Future.wait([
      _storage.delete(key: AppConstants.accessTokenKey, aOptions: _options),
      _storage.delete(key: AppConstants.refreshTokenKey, aOptions: _options),
    ]);
  }
}
