import '../../domain/entities/vpn_profile.dart';

/// JSON ↔ [VpnProfile] mapper for GET /mobile/v1/profile responses.
class VpnProfileModel extends VpnProfile {
  const VpnProfileModel({
    required super.username,
    required super.subscriptionUrl,
    required super.trafficUsedGb,
    required super.trafficLimitGb,
    required super.trafficUsedPercent,
    required super.expiresAt,
    required super.isActive,
    required super.status,
  });

  factory VpnProfileModel.fromJson(Map<String, dynamic> json) {
    return VpnProfileModel(
      username: json['username'] as String?,
      subscriptionUrl: json['subscription_url'] as String?,
      trafficUsedGb: (json['traffic_used_gb'] as num?)?.toDouble() ?? 0.0,
      trafficLimitGb: (json['traffic_limit_gb'] as num?)?.toInt() ?? 0,
      trafficUsedPercent:
          (json['traffic_used_percent'] as num?)?.toDouble() ?? 0.0,
      expiresAt: json['expires_at'] == null
          ? null
          : DateTime.tryParse(json['expires_at'] as String),
      isActive: json['is_active'] as bool? ?? false,
      status: json['status'] as String? ?? 'no_subscription',
    );
  }
}
