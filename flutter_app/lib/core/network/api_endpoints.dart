/// API endpoint paths, relative to [AppConstants.apiPrefix].
class ApiEndpoints {
  ApiEndpoints._();

  // Auth
  static const String registerEmail = '/cabinet/auth/email/register/standalone';
  static const String loginEmail = '/cabinet/auth/email/login';
  static const String refreshToken = '/cabinet/auth/refresh';
  static const String logout = '/cabinet/auth/logout';
  static const String verifyEmail = '/cabinet/auth/email/verify';
  static const String forgotPassword = '/cabinet/auth/password/forgot';
  static const String resetPassword = '/cabinet/auth/password/reset';

  // User profile
  static const String me = '/cabinet/auth/me';

  // Mobile API v1 — dedicated endpoints for the Flutter app
  static const String mobileTariffs = '/mobile/v1/tariffs';
  static const String mobileServers = '/mobile/v1/servers';
  static const String mobileProfile = '/mobile/v1/profile';
}
