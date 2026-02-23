class ApiConfig {
  static const String baseUrl = 'http://localhost:8000/cabinet';
  
  static String get apiUrl {
    const env = String.fromEnvironment('ENV', defaultValue: 'dev');
    switch (env) {
      case 'prod':
        return 'https://api.yourdomain.com/cabinet';
      case 'staging':
        return 'https://staging-api.yourdomain.com/cabinet';
      default:
        return baseUrl;
    }
  }
  
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
}
