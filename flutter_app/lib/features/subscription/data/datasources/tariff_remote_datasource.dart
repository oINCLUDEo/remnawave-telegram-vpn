import 'package:dio/dio.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_endpoints.dart';
import '../models/tariff_plan_model.dart';

/// Fetches purchase options (tariffs) from the cabinet API.
class TariffRemoteDataSource {
  const TariffRemoteDataSource({required ApiClient apiClient})
      : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// Calls [ApiEndpoints.purchaseOptions] and returns parsed tariff plans.
  ///
  /// Throws [DioException] on network errors or non-2xx responses.
  Future<({List<TariffPlanModel> plans, String salesMode})>
      getPurchaseOptions() async {
    final response = await _apiClient.dio
        .get<Map<String, dynamic>>(ApiEndpoints.purchaseOptions);

    final data = response.data ?? {};
    final salesMode = data['sales_mode'] as String? ?? 'classic';

    final rawTariffs = data['tariffs'] as List<dynamic>? ?? [];
    final plans = rawTariffs
        .whereType<Map<String, dynamic>>()
        .map(TariffPlanModel.fromJson)
        .where((t) => t.periods.isNotEmpty)
        .toList();

    return (plans: plans, salesMode: salesMode);
  }
}
