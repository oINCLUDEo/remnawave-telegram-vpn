class ApiConfig {
  // Base URL for API - can be changed for production
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8081',
  );
  
  // API Endpoints
  // Cabinet Auth endpoints
  static const String authLogin = '/cabinet/auth/email/login';
  static const String authRegister = '/cabinet/auth/email/register/standalone';
  static const String authRefresh = '/cabinet/auth/refresh';
  
  // Cabinet User endpoints
  static const String usersMe = '/cabinet/auth/me';
  static const String userSubscription = '/cabinet/subscription/current';
  
  // Other Cabinet endpoints
  static const String subscriptions = '/cabinet/subscription';
  static const String servers = '/cabinet/info/servers';
  
  // Timeout settings
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
  
  // Headers
  static Map<String, String> get headers => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };
  
  static Map<String, String> authHeaders(String token) => {
    ...headers,
    'Authorization': 'Bearer $token',
  };
}
