import 'package:dio/dio.dart';

import '../../../../core/errors/failures.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_endpoints.dart';
import '../../../../core/storage/secure_storage_service.dart';
import '../models/auth_response_model.dart';
import '../models/user_model.dart';

/// Remote data source — talks directly to the backend REST API.
class AuthRemoteDataSource {
  const AuthRemoteDataSource({
    required ApiClient apiClient,
    required SecureStorageService storage,
  })  : _apiClient = apiClient,
        _storage = storage;

  final ApiClient _apiClient;
  final SecureStorageService _storage;

  Dio get _dio => _apiClient.dio;

  /// POST /cabinet/auth/register
  Future<Map<String, dynamic>> registerWithEmail({
    required String email,
    required String password,
    String? firstName,
    String language = 'ru',
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        ApiEndpoints.registerEmail,
        data: {
          'email': email,
          'password': password,
          if (firstName != null && firstName.isNotEmpty) 'first_name': firstName,
          'language': language,
        },
      );
      return response.data!;
    } on DioException catch (e) {
      throw _mapDioError(e);
    }
  }

  /// POST /cabinet/auth/login
  Future<AuthResponseModel> loginWithEmail({
    required String email,
    required String password,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        ApiEndpoints.loginEmail,
        data: {'email': email, 'password': password},
      );
      final model = AuthResponseModel.fromJson(response.data!);
      await _storage.saveTokens(
        accessToken: model.accessToken,
        refreshToken: model.refreshToken,
      );
      return model;
    } on DioException catch (e) {
      throw _mapDioError(e);
    }
  }

  /// POST /cabinet/auth/refresh
  Future<AuthResponseModel> refreshToken(String refreshToken) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        ApiEndpoints.refreshToken,
        data: {'refresh_token': refreshToken},
      );
      final model = AuthResponseModel.fromJson(response.data!);
      await _storage.saveTokens(
        accessToken: model.accessToken,
        refreshToken: model.refreshToken,
      );
      return model;
    } on DioException catch (e) {
      throw _mapDioError(e);
    }
  }

  /// GET /cabinet/user/me
  Future<UserModel> getProfile() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(ApiEndpoints.me);
      return UserModel.fromJson(response.data!);
    } on DioException catch (e) {
      throw _mapDioError(e);
    }
  }

  // Maps a DioException to a domain [Failure].
  Failure _mapDioError(DioException e) {
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      return const NetworkFailure();
    }
    final statusCode = e.response?.statusCode;
    if (statusCode == 401) {
      return const AuthFailure();
    }
    final detail = _extractDetail(e.response?.data);
    return ServerFailure(detail ?? 'Ошибка сервера', statusCode: statusCode);
  }

  String? _extractDetail(dynamic data) {
    if (data is Map<String, dynamic>) {
      return data['detail'] as String?;
    }
    return null;
  }
}
