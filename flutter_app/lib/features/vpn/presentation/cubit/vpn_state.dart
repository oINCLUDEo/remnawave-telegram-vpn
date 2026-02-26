import 'package:equatable/equatable.dart';

import '../../domain/entities/vpn_profile.dart';

/// Whether the user has initiated a VPN connection via Happ.
enum VpnConnectionStatus {
  /// Default — user has not yet connected this session.
  disconnected,

  /// Happ deep link was just launched; waiting for user to return.
  launching,

  /// User has returned to the app after launching Happ — optimistically connected.
  connected,
}

/// Immutable state for [VpnCubit].
class VpnState extends Equatable {
  const VpnState({
    this.profile,
    this.isLoadingProfile = false,
    this.connectionStatus = VpnConnectionStatus.disconnected,
    this.error,
  });

  /// The user's subscription profile.  Null when not yet loaded or unauthenticated.
  final VpnProfile? profile;

  final bool isLoadingProfile;
  final VpnConnectionStatus connectionStatus;

  /// Non-null when an error occurred (network, no subscription, etc.).
  final String? error;

  // ── Convenience getters ───────────────────────────────────────────────────

  bool get isConnected => connectionStatus == VpnConnectionStatus.connected;
  bool get isLaunching => connectionStatus == VpnConnectionStatus.launching;
  bool get hasProfile => profile != null;
  bool get hasSubscription => profile?.hasSubscription == true;

  VpnState copyWith({
    VpnProfile? profile,
    bool? isLoadingProfile,
    VpnConnectionStatus? connectionStatus,
    String? Function()? error,
  }) {
    return VpnState(
      profile: profile ?? this.profile,
      isLoadingProfile: isLoadingProfile ?? this.isLoadingProfile,
      connectionStatus: connectionStatus ?? this.connectionStatus,
      error: error != null ? error() : this.error,
    );
  }

  @override
  List<Object?> get props =>
      [profile, isLoadingProfile, connectionStatus, error];
}
