import 'package:equatable/equatable.dart';

/// Base class for all VPN connection states.
sealed class VpnState extends Equatable {
  const VpnState();
}

/// No active VPN tunnel.
final class VpnDisconnected extends VpnState {
  const VpnDisconnected();

  @override
  List<Object?> get props => [];
}

/// Tunnel is being established.
final class VpnConnecting extends VpnState {
  const VpnConnecting();

  @override
  List<Object?> get props => [];
}

/// Tunnel is active and traffic is routed through the VPN.
final class VpnConnected extends VpnState {
  const VpnConnected();

  @override
  List<Object?> get props => [];
}

/// Tunnel is being torn down.
final class VpnDisconnecting extends VpnState {
  const VpnDisconnecting();

  @override
  List<Object?> get props => [];
}
