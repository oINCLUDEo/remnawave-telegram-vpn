import '../../domain/entities/subscription.dart';
import 'server_info_model.dart';

/// JSON ↔ [Subscription] mapping.
class SubscriptionModel extends Subscription {
  const SubscriptionModel({
    required super.id,
    required super.status,
    required super.isTrial,
    required super.startDate,
    required super.endDate,
    required super.daysLeft,
    required super.hoursLeft,
    required super.timeLeftDisplay,
    required super.trafficLimitGb,
    required super.trafficUsedGb,
    required super.trafficUsedPercent,
    required super.deviceLimit,
    required super.autopayEnabled,
    required super.isActive,
    required super.isExpired,
    super.subscriptionUrl,
    super.tariffName,
    super.tariffId,
    super.servers,
  });

  factory SubscriptionModel.fromJson(Map<String, dynamic> json) {
    final serversList = (json['servers'] as List<dynamic>? ?? [])
        .map((s) => ServerInfoModel.fromJson(s as Map<String, dynamic>))
        .toList();

    return SubscriptionModel(
      id: json['id'] as int,
      status: json['status'] as String,
      isTrial: (json['is_trial'] as bool?) ?? false,
      startDate: DateTime.parse(json['start_date'] as String),
      endDate: DateTime.parse(json['end_date'] as String),
      daysLeft: (json['days_left'] as int?) ?? 0,
      hoursLeft: (json['hours_left'] as int?) ?? 0,
      timeLeftDisplay: (json['time_left_display'] as String?) ?? '',
      trafficLimitGb: (json['traffic_limit_gb'] as int?) ?? 0,
      trafficUsedGb: ((json['traffic_used_gb'] as num?) ?? 0).toDouble(),
      trafficUsedPercent:
          ((json['traffic_used_percent'] as num?) ?? 0).toDouble(),
      deviceLimit: (json['device_limit'] as int?) ?? 1,
      autopayEnabled: (json['autopay_enabled'] as bool?) ?? false,
      isActive: (json['is_active'] as bool?) ?? false,
      isExpired: (json['is_expired'] as bool?) ?? false,
      subscriptionUrl: json['subscription_url'] as String?,
      tariffName: json['tariff_name'] as String?,
      tariffId: json['tariff_id'] as int?,
      servers: serversList,
    );
  }
}
