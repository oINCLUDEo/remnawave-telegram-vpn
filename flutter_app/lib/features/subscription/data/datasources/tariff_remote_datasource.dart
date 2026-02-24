import 'package:dio/dio.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_endpoints.dart';
import '../models/tariff_plan_model.dart';

/// Fetches tariff plans from the cabinet API.
///
/// Strategy:
/// 1. Try the authenticated [ApiEndpoints.purchaseOptions] endpoint.
/// 2. If the server returns 401/403 (no valid token), automatically retry
///    with the anonymous [ApiEndpoints.publicTariffs] endpoint.
class TariffRemoteDataSource {
  const TariffRemoteDataSource({required ApiClient apiClient})
      : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// Returns tariff plans, falling back to the public endpoint on 401/403.
  ///
  /// Throws [DioException] on network errors or non-2xx responses other than
  /// 401/403 (which are handled internally by the fallback).
  Future<({List<TariffPlanModel> plans, String salesMode})>
      getPurchaseOptions() async {
    try {
      return await _fetchFrom(ApiEndpoints.purchaseOptions);
    } on DioException catch (e) {
      final status = e.response?.statusCode;
      if (status == 401 || status == 403) {
        // Not authenticated — retry with the public endpoint (no auth needed).
        return await _fetchFrom(ApiEndpoints.publicTariffs);
      }
      rethrow;
    }
  }

  Future<({List<TariffPlanModel> plans, String salesMode})> _fetchFrom(
      String path) async {
    final response =
        await _apiClient.dio.get<Map<String, dynamic>>(path);

    final data = response.data ?? {};
    final salesMode = data['sales_mode'] as String? ?? 'tariffs';

    final rawTariffs = data['tariffs'] as List<dynamic>? ?? [];
    final plans = rawTariffs
        .whereType<Map<String, dynamic>>()
        .map(TariffPlanModel.fromJson)
        .where((t) => t.periods.isNotEmpty)
        .toList();

    return (plans: plans, salesMode: salesMode);
  }
}
