import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'api_config.dart';

class ApiClient {
  late final Dio _dio;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  
  ApiClient() {
    _dio = Dio(BaseOptions(
      baseUrl: ApiConfig.apiUrl,
      connectTimeout: ApiConfig.connectTimeout,
      receiveTimeout: ApiConfig.receiveTimeout,
      headers: {'Content-Type': 'application/json'},
    ));
    
    _setupInterceptors();
  }
  
  void _setupInterceptors() {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: 'access_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          final refreshed = await _refreshToken();
          if (refreshed) {
            final opts = error.requestOptions;
            final token = await _storage.read(key: 'access_token');
            opts.headers['Authorization'] = 'Bearer $token';
            try {
              final response = await _dio.fetch(opts);
              return handler.resolve(response);
            } catch (e) {
              return handler.reject(error);
            }
          }
        }
        handler.next(error);
      },
    ));
  }
  
  Future<bool> _refreshToken() async {
    try {
      final refreshToken = await _storage.read(key: 'refresh_token');
      if (refreshToken == null) return false;
      
      final response = await _dio.post('/auth/refresh', data: {
        'refresh_token': refreshToken,
      });
      
      final newToken = response.data['access_token'];
      await _storage.write(key: 'access_token', value: newToken);
      return true;
    } catch (e) {
      await _storage.deleteAll();
      return false;
    }
  }
  
  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await _dio.post('/auth/login-email', data: {
      'email': email,
      'password': password,
    });
    return response.data;
  }
  
  Future<Map<String, dynamic>> register(String email, String password, String firstName) async {
    final response = await _dio.post('/auth/register-email', data: {
      'email': email,
      'password': password,
      'first_name': firstName,
    });
    return response.data;
  }
  
  Future<Map<String, dynamic>> getMe() async {
    final response = await _dio.get('/auth/me');
    return response.data;
  }
  
  Future<Map<String, dynamic>> getBalance() async {
    final response = await _dio.get('/balance');
    return response.data;
  }
  
  Future<Map<String, dynamic>> topUp(double amount, String paymentMethod) async {
    final response = await _dio.post('/balance/top-up', data: {
      'amount_rubles': amount,
      'payment_method': paymentMethod,
      'return_url': 'vpnapp://payment/callback',
    });
    return response.data;
  }
  
  Future<List<dynamic>> getTransactions({int page = 1, int perPage = 20}) async {
    final response = await _dio.get('/balance/transactions', queryParameters: {
      'page': page,
      'per_page': perPage,
    });
    return response.data['items'];
  }
  
  Future<Map<String, dynamic>?> getSubscription() async {
    try {
      final response = await _dio.get('/subscription');
      return response.data;
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }
  
  Future<List<dynamic>> getTariffs() async {
    final response = await _dio.get('/subscription/tariffs');
    return response.data['tariffs'];
  }
  
  Future<Map<String, dynamic>> purchaseTariff(int tariffId, String serverUuid) async {
    final response = await _dio.post('/subscription/purchase-tariff', data: {
      'tariff_id': tariffId,
      'server_squad_uuid': serverUuid,
    });
    return response.data;
  }
  
  Future<Map<String, dynamic>> activateTrial(String serverUuid, int devicesCount) async {
    final response = await _dio.post('/subscription/activate-trial', data: {
      'server_squad_uuid': serverUuid,
      'devices_count': devicesCount,
    });
    return response.data;
  }
  
  Future<Map<String, dynamic>> getReferralStats() async {
    final response = await _dio.get('/referral/stats');
    return response.data;
  }
  
  Future<List<dynamic>> getReferrals({int page = 1, int perPage = 20}) async {
    final response = await _dio.get('/referral/referrals', queryParameters: {
      'page': page,
      'per_page': perPage,
    });
    return response.data['referrals'];
  }
  
  Future<Map<String, dynamic>> activatePromocode(String code) async {
    final response = await _dio.post('/promocode/activate', data: {
      'code': code,
    });
    return response.data;
  }
}
