import 'package:dio/dio.dart';

import '../../../../core/errors/failures.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_endpoints.dart';
import '../models/renewal_option_model.dart';
import '../models/subscription_model.dart';

/// Remote data source for subscription data.
class SubscriptionRemoteDataSource {
  const SubscriptionRemoteDataSource({required ApiClient apiClient})
      : _apiClient = apiClient;

  final ApiClient _apiClient;

  Dio get _dio => _apiClient.dio;

  /// GET /cabinet/subscription — returns null when user has no subscription.
  Future<SubscriptionModel?> getSubscription() async {
    try {
      final response =
          await _dio.get<Map<String, dynamic>>(ApiEndpoints.subscription);
      final data = response.data!;
      final hasSubscription = data['has_subscription'] as bool? ?? false;
      if (!hasSubscription) return null;
      final subJson = data['subscription'] as Map<String, dynamic>?;
      if (subJson == null) return null;
      return SubscriptionModel.fromJson(subJson);
    } on DioException catch (e) {
      throw _mapDioError(e);
    }
  }

  /// GET /cabinet/subscription/renewal-options
  Future<List<RenewalOptionModel>> getRenewalOptions() async {
    try {
      final response = await _dio
          .get<List<dynamic>>(ApiEndpoints.subscriptionRenewalOptions);
      final list = response.data ?? [];
      return list
          .map((e) =>
              RenewalOptionModel.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _mapDioError(e);
    }
  }

  Failure _mapDioError(DioException e) {
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      return const NetworkFailure();
    }
    if (e.response?.statusCode == 401) return const AuthFailure();
    final detail = (e.response?.data is Map<String, dynamic>)
        ? (e.response!.data as Map<String, dynamic>)['detail'] as String?
        : null;
    return ServerFailure(
      detail ?? 'Ошибка сервера',
      statusCode: e.response?.statusCode,
    );
  }
}
