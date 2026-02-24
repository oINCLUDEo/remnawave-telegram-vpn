import 'package:equatable/equatable.dart';

import 'server_info.dart';

/// Active subscription entity — mirrors backend [SubscriptionData].
class Subscription extends Equatable {
  const Subscription({
    required this.id,
    required this.status,
    required this.isTrial,
    required this.startDate,
    required this.endDate,
    required this.daysLeft,
    required this.hoursLeft,
    required this.timeLeftDisplay,
    required this.trafficLimitGb,
    required this.trafficUsedGb,
    required this.trafficUsedPercent,
    required this.deviceLimit,
    required this.autopayEnabled,
    required this.isActive,
    required this.isExpired,
    this.subscriptionUrl,
    this.tariffName,
    this.tariffId,
    this.servers = const [],
  });

  final int id;
  final String status;
  final bool isTrial;
  final DateTime startDate;
  final DateTime endDate;
  final int daysLeft;
  final int hoursLeft;

  /// Human-readable time remaining, e.g. "2д 5ч" or "5ч 30м".
  final String timeLeftDisplay;

  /// 0 means unlimited.
  final int trafficLimitGb;
  final double trafficUsedGb;
  final double trafficUsedPercent;
  final int deviceLimit;
  final bool autopayEnabled;
  final bool isActive;
  final bool isExpired;
  final String? subscriptionUrl;
  final String? tariffName;
  final int? tariffId;
  final List<ServerInfo> servers;

  bool get isUnlimited => trafficLimitGb == 0;

  @override
  List<Object?> get props => [
        id,
        status,
        isTrial,
        startDate,
        endDate,
        daysLeft,
        hoursLeft,
        timeLeftDisplay,
        trafficLimitGb,
        trafficUsedGb,
        trafficUsedPercent,
        deviceLimit,
        autopayEnabled,
        isActive,
        isExpired,
        subscriptionUrl,
        tariffName,
        tariffId,
        servers,
      ];
}
