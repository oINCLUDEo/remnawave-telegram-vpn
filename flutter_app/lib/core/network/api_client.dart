import 'package:dio/dio.dart';

import '../constants/app_constants.dart';
import '../storage/secure_storage_service.dart';
import 'api_endpoints.dart';

/// Dio HTTP client pre-configured for the backend API.
///
/// Automatically attaches the JWT access token to every request and
/// handles transparent token refresh when a 401 is received.
class ApiClient {
  ApiClient({
    required SecureStorageService storage,
    String? baseUrl,
  })  : _storage = storage,
        _dio = _buildDio(baseUrl ?? AppConstants.defaultBaseUrl);

  final SecureStorageService _storage;
  final Dio _dio;

  static Dio _buildDio(String baseUrl) {
    return Dio(
      BaseOptions(
        baseUrl: '$baseUrl${AppConstants.apiPrefix}',
        connectTimeout: const Duration(milliseconds: AppConstants.connectTimeoutMs),
        receiveTimeout: const Duration(milliseconds: AppConstants.receiveTimeoutMs),
        headers: {'Content-Type': 'application/json'},
      ),
    );
  }

  /// Returns a configured [Dio] instance. Call [_attachInterceptors] before
  /// using this getter to ensure the interceptors are only added once.
  Dio get dio => _dio;

  /// Attaches auth + refresh interceptors.  Must be called once after
  /// construction (cannot be done in the constructor because the interceptor
  /// needs a reference to [this]).
  void attachInterceptors() {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: _onRequest,
        onError: _onError,
      ),
    );
  }

  Future<void> _onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await _storage.readAccessToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  Future<void> _onError(
    DioException error,
    ErrorInterceptorHandler handler,
  ) async {
    if (error.response?.statusCode != 401) {
      handler.next(error);
      return;
    }

    // Attempt silent token refresh.
    final refreshToken = await _storage.readRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      handler.next(error);
      return;
    }

    try {
      final response = await _dio.post<Map<String, dynamic>>(
        ApiEndpoints.refreshToken,
        data: {'refresh_token': refreshToken},
        options: Options(headers: {'Authorization': null}),
      );

      final newAccess = response.data?['access_token'] as String?;
      final newRefresh = response.data?['refresh_token'] as String?;
      if (newAccess == null || newRefresh == null) {
        handler.next(error);
        return;
      }

      await _storage.saveTokens(
        accessToken: newAccess,
        refreshToken: newRefresh,
      );

      // Retry the original request with the new token.
      final retryOptions = error.requestOptions
        ..headers['Authorization'] = 'Bearer $newAccess';
      final retryResponse = await _dio.fetch<dynamic>(retryOptions);
      handler.resolve(retryResponse);
    } on DioException catch (_) {
      await _storage.clearTokens();
      handler.next(error);
    }
  }
}
