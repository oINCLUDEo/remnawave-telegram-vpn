import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../constants/app_constants.dart';

/// Thin wrapper around [FlutterSecureStorage] scoped to auth tokens.
///
/// Tokens are kept in an in-memory cache that is populated on [saveTokens]
/// and cleared on [clearTokens].  The in-memory layer is checked first on
/// every read so that the platform Keystore (which can hang indefinitely on
/// some Android devices / emulators when using encryptedSharedPreferences) is
/// only hit on a cold app-start — and even then a [_kStorageTimeout] timeout
/// ensures it can never block forever.
class SecureStorageService {
  SecureStorageService(this._storage);

  final FlutterSecureStorage _storage;

  static const _options = AndroidOptions(
    encryptedSharedPreferences: true,
  );

  /// Max time to wait for a platform Keystore read before giving up.
  static const _kStorageTimeout = Duration(seconds: 3);

  // ── In-memory cache ──────────────────────────────────────────────────────
  String? _cachedAccessToken;
  String? _cachedRefreshToken;

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    // Update the in-memory cache synchronously so subsequent reads never
    // need to hit the platform storage.
    _cachedAccessToken = accessToken;
    _cachedRefreshToken = refreshToken;

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

  Future<String?> readAccessToken() async {
    if (_cachedAccessToken != null) return _cachedAccessToken;
    // Cold-start path: read from platform storage with a hard timeout.
    try {
      _cachedAccessToken = await _storage
          .read(key: AppConstants.accessTokenKey, aOptions: _options)
          .timeout(_kStorageTimeout);
    } catch (_) {
      // Timeout or platform error — return null so callers can proceed.
      return null;
    }
    return _cachedAccessToken;
  }

  Future<String?> readRefreshToken() async {
    if (_cachedRefreshToken != null) return _cachedRefreshToken;
    try {
      _cachedRefreshToken = await _storage
          .read(key: AppConstants.refreshTokenKey, aOptions: _options)
          .timeout(_kStorageTimeout);
    } catch (_) {
      return null;
    }
    return _cachedRefreshToken;
  }

  Future<void> clearTokens() async {
    _cachedAccessToken = null;
    _cachedRefreshToken = null;
    await Future.wait([
      _storage.delete(key: AppConstants.accessTokenKey, aOptions: _options),
      _storage.delete(key: AppConstants.refreshTokenKey, aOptions: _options),
    ]);
  }
}
