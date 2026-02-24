import 'package:flutter_bloc/flutter_bloc.dart';

import 'vpn_state.dart';

/// Manages the VPN connection state.
///
/// Currently operates in dev-mode: toggling locally without a real VPN tunnel.
/// Designed so real VPN logic can be plugged in by replacing [connect] /
/// [disconnect] implementations without touching any UI code.
class VpnCubit extends Cubit<VpnState> {
  VpnCubit() : super(const VpnDisconnected());

  /// Toggle the VPN connection.
  Future<void> toggleConnection() async {
    if (state is VpnConnected) {
      await disconnect();
    } else {
      await connect();
    }
  }

  /// Initiate a VPN connection.
  Future<void> connect() async {
    emit(const VpnConnecting());
    // TODO(vpn): replace with real tunnel connect call.
    await Future<void>.delayed(const Duration(milliseconds: 800));
    emit(const VpnConnected());
  }

  /// Tear down an active VPN connection.
  Future<void> disconnect() async {
    emit(const VpnDisconnecting());
    // TODO(vpn): replace with real tunnel disconnect call.
    await Future<void>.delayed(const Duration(milliseconds: 500));
    emit(const VpnDisconnected());
  }
}
