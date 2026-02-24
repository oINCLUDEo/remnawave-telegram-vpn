import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ulya_vpn/core/theme/app_theme.dart';
import 'package:ulya_vpn/features/home/presentation/pages/home_page.dart';
import 'package:ulya_vpn/features/home/presentation/widgets/vpn_connect_button.dart';
import 'package:ulya_vpn/features/home/presentation/widgets/server_card.dart';

Widget _buildUnderTest() {
  return MaterialApp(
    theme: AppTheme.dark,
    home: const HomePage(),
  );
}

void main() {
  testWidgets('HomePage renders VpnConnectButton', (tester) async {
    await tester.pumpWidget(_buildUnderTest());
    expect(find.byType(VpnConnectButton), findsOneWidget);
  });

  testWidgets('HomePage renders ServerCard', (tester) async {
    await tester.pumpWidget(_buildUnderTest());
    expect(find.byType(ServerCard), findsOneWidget);
  });

  testWidgets('HomePage shows disconnected status initially', (tester) async {
    await tester.pumpWidget(_buildUnderTest());
    expect(find.text('Отключен'), findsOneWidget);
  });

  testWidgets('tapping connect button transitions to connecting state',
      (tester) async {
    await tester.pumpWidget(_buildUnderTest());

    // Tap the connect button.
    await tester.tap(find.byType(VpnConnectButton));
    await tester.pump(); // trigger state emit

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('status changes to Защищено after connection completes',
      (tester) async {
    await tester.pumpWidget(_buildUnderTest());

    await tester.tap(find.byType(VpnConnectButton));
    await tester.pumpAndSettle(); // wait for async connection delay

    expect(find.text('Защищено'), findsOneWidget);
  });
}
