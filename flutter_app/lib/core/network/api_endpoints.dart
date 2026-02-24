/// API endpoint paths, relative to [AppConstants.apiPrefix].
class ApiEndpoints {
  ApiEndpoints._();

  // Auth
  static const String registerEmail = '/cabinet/auth/register';
  static const String loginEmail = '/cabinet/auth/login';
  static const String refreshToken = '/cabinet/auth/refresh';
  static const String logout = '/cabinet/auth/logout';
  static const String verifyEmail = '/cabinet/auth/verify-email';
  static const String forgotPassword = '/cabinet/auth/forgot-password';
  static const String resetPassword = '/cabinet/auth/reset-password';

  // User profile
  static const String me = '/cabinet/user/me';
}
