/// Application-wide constants.
class AppConstants {
  AppConstants._();

  // API
  static const String defaultBaseUrl = 'http://localhost:8000';
  static const String apiPrefix = '/api/v1';
  static const int connectTimeoutMs = 15000;
  static const int receiveTimeoutMs = 30000;

  // Secure storage keys
  static const String accessTokenKey = 'access_token';
  static const String refreshTokenKey = 'refresh_token';

  // Token refresh threshold (seconds before expiry to trigger refresh)
  static const int tokenRefreshThresholdSeconds = 60;

  // Password rules (mirrors backend)
  static const int passwordMinLength = 8;
  static const int passwordMaxLength = 128;
}
