import '../../domain/entities/server_info.dart';

/// JSON ↔ [ServerInfo] mapping.
class ServerInfoModel extends ServerInfo {
  const ServerInfoModel({
    required super.uuid,
    required super.name,
    super.countryCode,
  });

  factory ServerInfoModel.fromJson(Map<String, dynamic> json) => ServerInfoModel(
        uuid: json['uuid'] as String,
        name: json['name'] as String,
        countryCode: json['country_code'] as String?,
      );
}
