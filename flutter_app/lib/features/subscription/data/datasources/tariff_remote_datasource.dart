import 'package:dio/dio.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_endpoints.dart';
import '../models/tariff_plan_model.dart';

/// Fetches tariff plans from the dedicated Mobile API v1.
///
/// The [ApiEndpoints.mobileTariffs] endpoint is always public — no
/// authentication is required.  When a valid Bearer token is present it
/// is forwarded automatically by [ApiClient] and the server applies the
/// authenticated user's promo-group discounts.  When called anonymously
/// the server applies the default promo-group discounts instead.
class TariffRemoteDataSource {
  const TariffRemoteDataSource({required ApiClient apiClient})
      : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// Returns tariff plans from the Mobile API.
  ///
  /// Throws [DioException] on network errors or non-2xx responses.
  Future<({List<TariffPlanModel> plans, String salesMode})>
      getPurchaseOptions() async {
    final response = await _apiClient.dio
        .get<Map<String, dynamic>>(ApiEndpoints.mobileTariffs);

    final data = response.data ?? {};
    // Mobile API always uses tariffs sales mode.
    const salesMode = 'tariffs';

    final rawTariffs = data['tariffs'] as List<dynamic>? ?? [];
    final plans = rawTariffs
        .whereType<Map<String, dynamic>>()
        .map(TariffPlanModel.fromJson)
        .where((t) => t.periods.isNotEmpty)
        .toList();

    return (plans: plans, salesMode: salesMode);
  }
}
