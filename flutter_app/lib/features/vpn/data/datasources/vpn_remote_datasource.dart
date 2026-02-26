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
}
