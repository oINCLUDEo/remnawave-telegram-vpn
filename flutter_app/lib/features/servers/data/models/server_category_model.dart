import '../../domain/entities/server_category_entity.dart';
import 'server_model.dart';

/// JSON-deserialisable version of [ServerCategoryEntity].
class ServerCategoryModel extends ServerCategoryEntity {
  const ServerCategoryModel({
    required super.id,
    required super.name,
    required super.subtitle,
    required super.serverCount,
    required super.servers,
  });

  factory ServerCategoryModel.fromJson(Map<String, dynamic> json) {
    final serversJson = json['servers'] as List<dynamic>;
    return ServerCategoryModel(
      id: json['id'] as String,
      name: json['name'] as String,
      subtitle: json['subtitle'] as String,
      serverCount: json['server_count'] as int,
      servers: serversJson
          .map((e) => ServerModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
