import '../../domain/entities/server_entity.dart';

/// JSON-deserialisable version of [ServerEntity].
class ServerModel extends ServerEntity {
  const ServerModel({
    required super.id,
    required super.name,
    super.countryCode,
    required super.flag,
    required super.category,
    required super.isAvailable,
    required super.loadPercent,
    required super.qualityLevel,
  });

  factory ServerModel.fromJson(Map<String, dynamic> json) {
    return ServerModel(
      id: json['id'] as int,
      name: json['name'] as String,
      countryCode: json['country_code'] as String?,
      flag: json['flag'] as String,
      category: json['category'] as String,
      isAvailable: json['is_available'] as bool,
      loadPercent: json['load_percent'] as int,
      qualityLevel: json['quality_level'] as int,
    );
  }
}
