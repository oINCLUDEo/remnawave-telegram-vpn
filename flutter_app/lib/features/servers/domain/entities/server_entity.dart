import 'package:equatable/equatable.dart';

/// A single VPN server as returned by the mobile API.
class ServerEntity extends Equatable {
  const ServerEntity({
    required this.id,
    required this.name,
    this.countryCode,
    required this.flag,
    required this.category,
    required this.isAvailable,
    required this.loadPercent,
    required this.qualityLevel,
  });

  final int id;
  final String name;
  final String? countryCode;

  /// Flag emoji (e.g. "🇩🇪") or "🌐" when country is unknown.
  final String flag;

  /// Category slug: "general", "whitelist", "youtube", "premium", …
  final String category;

  /// False when the server is at capacity or disabled by the admin.
  final bool isAvailable;

  /// 0–100 load percentage based on current / max users.
  final int loadPercent;

  /// 1–5 quality indicator (5 = best). Maps directly to SignalIndicator.level.
  final int qualityLevel;

  @override
  List<Object?> get props => [
        id,
        name,
        countryCode,
        flag,
        category,
        isAvailable,
        loadPercent,
        qualityLevel,
      ];
}
