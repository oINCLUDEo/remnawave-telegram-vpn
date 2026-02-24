import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ulya_vpn/features/home/presentation/cubit/vpn_cubit.dart';
import 'package:ulya_vpn/features/home/presentation/cubit/vpn_state.dart';

void main() {
  group('VpnCubit', () {
    test('initial state is VpnDisconnected', () {
      expect(VpnCubit().state, isA<VpnDisconnected>());
    });

    blocTest<VpnCubit, VpnState>(
      'connect() emits [VpnConnecting, VpnConnected]',
      build: VpnCubit.new,
      act: (cubit) => cubit.connect(),
      expect: () => [isA<VpnConnecting>(), isA<VpnConnected>()],
    );

    blocTest<VpnCubit, VpnState>(
      'disconnect() emits [VpnDisconnecting, VpnDisconnected] when connected',
      build: VpnCubit.new,
      seed: () => const VpnConnected(),
      act: (cubit) => cubit.disconnect(),
      expect: () => [isA<VpnDisconnecting>(), isA<VpnDisconnected>()],
    );

    blocTest<VpnCubit, VpnState>(
      'toggleConnection() connects when disconnected',
      build: VpnCubit.new,
      act: (cubit) => cubit.toggleConnection(),
      expect: () => [isA<VpnConnecting>(), isA<VpnConnected>()],
    );

    blocTest<VpnCubit, VpnState>(
      'toggleConnection() disconnects when connected',
      build: VpnCubit.new,
      seed: () => const VpnConnected(),
      act: (cubit) => cubit.toggleConnection(),
      expect: () => [isA<VpnDisconnecting>(), isA<VpnDisconnected>()],
    );
  });
}
