class Subscription {
  final int id;
  final String status;
  final String actualStatus;
  final bool isTrial;
  final DateTime startDate;
  final DateTime endDate;
  final int trafficLimitGb;
  final double trafficUsedGb;
  final int deviceLimit;
  final bool autopayEnabled;
  final int? autopayDaysBefore;
  final String? subscriptionUrl;
  final String? subscriptionCryptoLink;
  final List<String> connectedSquads;

  Subscription({
    required this.id,
    required this.status,
    required this.actualStatus,
    required this.isTrial,
    required this.startDate,
    required this.endDate,
    required this.trafficLimitGb,
    required this.trafficUsedGb,
    required this.deviceLimit,
    required this.autopayEnabled,
    this.autopayDaysBefore,
    this.subscriptionUrl,
    this.subscriptionCryptoLink,
    required this.connectedSquads,
  });

  factory Subscription.fromJson(Map<String, dynamic> json) {
    return Subscription(
      id: json['id'] as int,
      status: json['status'] as String,
      actualStatus: json['actual_status'] as String,
      isTrial: json['is_trial'] as bool,
      startDate: DateTime.parse(json['start_date'] as String),
      endDate: DateTime.parse(json['end_date'] as String),
      trafficLimitGb: json['traffic_limit_gb'] as int,
      trafficUsedGb: (json['traffic_used_gb'] as num).toDouble(),
      deviceLimit: json['device_limit'] as int,
      autopayEnabled: json['autopay_enabled'] as bool,
      autopayDaysBefore: json['autopay_days_before'] as int?,
      subscriptionUrl: json['subscription_url'] as String?,
      subscriptionCryptoLink: json['subscription_crypto_link'] as String?,
      connectedSquads: (json['connected_squads'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'status': status,
      'actual_status': actualStatus,
      'is_trial': isTrial,
      'start_date': startDate.toIso8601String(),
      'end_date': endDate.toIso8601String(),
      'traffic_limit_gb': trafficLimitGb,
      'traffic_used_gb': trafficUsedGb,
      'device_limit': deviceLimit,
      'autopay_enabled': autopayEnabled,
      'autopay_days_before': autopayDaysBefore,
      'subscription_url': subscriptionUrl,
      'subscription_crypto_link': subscriptionCryptoLink,
      'connected_squads': connectedSquads,
    };
  }

  bool get isActive => actualStatus == 'active';
  bool get isExpired => actualStatus == 'expired';
  
  int get daysRemaining {
    final now = DateTime.now();
    if (endDate.isBefore(now)) return 0;
    return endDate.difference(now).inDays;
  }

  double get trafficRemainingGb {
    final remaining = trafficLimitGb - trafficUsedGb;
    return remaining > 0 ? remaining : 0;
  }

  double get trafficUsagePercent {
    if (trafficLimitGb == 0) return 0;
    return (trafficUsedGb / trafficLimitGb * 100).clamp(0, 100);
  }
}
