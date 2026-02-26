import 'package:equatable/equatable.dart';

/// The user's VPN subscription profile as returned by GET /mobile/v1/profile.
class VpnProfile extends Equatable {
  const VpnProfile({
    required this.username,
    required this.subscriptionUrl,
    required this.trafficUsedGb,
    required this.trafficLimitGb,
    required this.trafficUsedPercent,
    required this.expiresAt,
    required this.isActive,
    required this.status,
  });

  final String? username;

  /// Full Remnawave subscription URL, e.g. https://sub.example.com/AbCd
  /// Fetched and parsed by flutter_v2ray to start the in-app VPN tunnel.
  final String? subscriptionUrl;

  final double trafficUsedGb;

  /// 0 means unlimited.
  final int trafficLimitGb;

  /// 0–100 percentage of traffic consumed.
  final double trafficUsedPercent;

  final DateTime? expiresAt;
  final bool isActive;

  /// One of: "active" | "trial" | "expired" | "disabled" | "no_subscription"
  final String status;

  // ── Computed helpers ──────────────────────────────────────────────────────

  bool get hasSubscription => subscriptionUrl != null;

  bool get isUnlimitedTraffic => trafficLimitGb == 0;

  String get trafficUsedLabel => '${trafficUsedGb.toStringAsFixed(1)} ГБ';

  String get trafficLimitLabel =>
      trafficLimitGb == 0 ? '∞ ГБ' : '$trafficLimitGb ГБ';

  /// 0–1 fraction for LinearProgressIndicator.
  double get trafficFraction => (trafficUsedPercent / 100).clamp(0.0, 1.0);

  @override
  List<Object?> get props => [
        username,
        subscriptionUrl,
        trafficUsedGb,
        trafficLimitGb,
        trafficUsedPercent,
        expiresAt,
        isActive,
        status,
      ];
}
