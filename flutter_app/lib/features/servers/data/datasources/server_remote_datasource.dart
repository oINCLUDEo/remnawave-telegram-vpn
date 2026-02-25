import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_endpoints.dart';
import '../models/server_category_model.dart';

/// Fetches server data from the Mobile API v1.
class ServerRemoteDataSource {
  const ServerRemoteDataSource({required ApiClient apiClient})
      : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// Returns servers grouped by category from [ApiEndpoints.mobileServers].
  ///
  /// Throws a [DioException] on any network or HTTP error — the repository
  /// layer converts these to domain [Failure] types.
  Future<List<ServerCategoryModel>> getServers() async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      ApiEndpoints.mobileServers,
    );
    final data = response.data!;
    final categoriesJson = data['categories'] as List<dynamic>;
    return categoriesJson
        .map((e) => ServerCategoryModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
