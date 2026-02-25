import '../entities/server_category_entity.dart';

/// Contract for fetching the list of available VPN servers.
abstract class ServerRepository {
  /// Returns servers grouped into categories from the mobile API.
  ///
  /// Throws a [Failure] subclass on network / server errors.
  Future<List<ServerCategoryEntity>> getServers();
}
