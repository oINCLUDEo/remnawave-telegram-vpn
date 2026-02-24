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

  // Subscription
  static const String subscription = '/cabinet/subscription';
  static const String subscriptionRenewalOptions =
      '/cabinet/subscription/renewal-options';
}
