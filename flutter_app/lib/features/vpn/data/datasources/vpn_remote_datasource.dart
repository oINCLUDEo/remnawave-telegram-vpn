import 'package:dio/dio.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_endpoints.dart';
import '../../domain/entities/vpn_profile.dart';
import '../models/vpn_profile_model.dart';

/// Remote data source — calls GET /mobile/v1/profile.
///
/// The [ApiClient] automatically attaches the JWT bearer token when available.
/// On 401 (no valid session) a [DioException] with status 401 is thrown and
/// the cubit maps it to a "not authenticated" state — the UI then shows
/// "Нет активной подписки" without crashing.
class VpnRemoteDataSource {
  const VpnRemoteDataSource({required this.apiClient});

  final ApiClient apiClient;

  /// Fetches the authenticated user's VPN profile.
  /// Throws [DioException] on network/auth errors.
  Future<VpnProfile> getProfile() async {
    final response = await apiClient.dio.get<Map<String, dynamic>>(
      ApiEndpoints.mobileProfile,
    );
    return VpnProfileModel.fromJson(response.data!);
  }

  /// Fetches the user's parsed VPN proxy links via the backend proxy.
  ///
  /// The backend fetches the Remnawave subscription URL server-side,
  /// decodes it, and returns a clean list of vless:// / vmess:// etc. links.
  /// Returns an empty list if the endpoint returns 404 (no subscription).
  Future<List<String>> getVpnConfig() async {
    try {
      final response = await apiClient.dio.get<Map<String, dynamic>>(
        ApiEndpoints.mobileVpnConfig,
      );
      final data = response.data ?? {};
      final raw = data['proxy_links'] as List<dynamic>? ?? [];
      return raw.cast<String>();
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return [];
      rethrow;
    }
  }
}
