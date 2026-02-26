import 'package:equatable/equatable.dart';

import '../../domain/entities/vpn_profile.dart';

/// VPN tunnel state.
enum VpnConnectionStatus {
  /// No active tunnel — initial state.
  disconnected,

  /// Fetching subscription + establishing tunnel.
  connecting,

  /// Tunnel is up and routing traffic.
  connected,

  /// Tearing down the tunnel.
  disconnecting,

  /// An error occurred during connect/disconnect.
  error,
}

/// Immutable state for [VpnCubit].
class VpnState extends Equatable {
  const VpnState({
    this.profile,
    this.isLoadingProfile = false,
    this.connectionStatus = VpnConnectionStatus.disconnected,
    this.downloadSpeed = '',
    this.uploadSpeed = '',
    this.connectionDuration = '',
    this.activeConfigRemark,
    this.error,
  });

  /// The user's subscription profile. Null when not yet loaded or unauthenticated.
  final VpnProfile? profile;

  final bool isLoadingProfile;
  final VpnConnectionStatus connectionStatus;

  /// Human-readable speed strings from the V2Ray status stream, e.g. "1.2 MB/s".
  final String downloadSpeed;
  final String uploadSpeed;

  /// HH:MM:SS connection uptime from V2Ray core.
  final String connectionDuration;

  /// Remark of the currently active proxy config.
  final String? activeConfigRemark;

  /// Non-null when an error occurred (network, no subscription, VPN permission denied, etc.).
  final String? error;

  // ── Convenience getters ──────────────────────────────────────────────────

  bool get isConnected => connectionStatus == VpnConnectionStatus.connected;
  bool get isConnecting => connectionStatus == VpnConnectionStatus.connecting;
  bool get isDisconnecting =>
      connectionStatus == VpnConnectionStatus.disconnecting;
  bool get hasProfile => profile != null;
  bool get hasSubscription => profile?.hasSubscription == true;

  VpnState copyWith({
    VpnProfile? profile,
    bool? isLoadingProfile,
    VpnConnectionStatus? connectionStatus,
    String? downloadSpeed,
    String? uploadSpeed,
    String? connectionDuration,
    String? activeConfigRemark,
    String? Function()? error,
  }) {
    return VpnState(
      profile: profile ?? this.profile,
      isLoadingProfile: isLoadingProfile ?? this.isLoadingProfile,
      connectionStatus: connectionStatus ?? this.connectionStatus,
      downloadSpeed: downloadSpeed ?? this.downloadSpeed,
      uploadSpeed: uploadSpeed ?? this.uploadSpeed,
      connectionDuration: connectionDuration ?? this.connectionDuration,
      activeConfigRemark: activeConfigRemark ?? this.activeConfigRemark,
      error: error != null ? error() : this.error,
    );
  }

  @override
  List<Object?> get props => [
        profile,
        isLoadingProfile,
        connectionStatus,
        downloadSpeed,
        uploadSpeed,
        connectionDuration,
        activeConfigRemark,
        error,
      ];
}
