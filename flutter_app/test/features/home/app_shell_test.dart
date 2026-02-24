import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ulya_vpn/core/theme/app_theme.dart';
import 'package:ulya_vpn/features/home/presentation/pages/app_shell.dart';
import 'package:ulya_vpn/features/home/presentation/pages/locations_page.dart';
import 'package:ulya_vpn/features/home/presentation/pages/subscription_page.dart';
import 'package:ulya_vpn/features/home/presentation/pages/settings_page.dart';

Widget _buildShell() {
  return MaterialApp(theme: AppTheme.dark, home: const AppShell());
}

void main() {
  testWidgets('AppShell starts on Home tab (index 1)', (tester) async {
    await tester.pumpWidget(_buildShell());
    // SubscriptionPage and LocationsPage are in the IndexedStack but not
    // visible; SettingsPage title should not appear.
    expect(find.text('Улья VPN'), findsNothing);
    expect(find.text('Отключен'), findsOneWidget);
  });

  testWidgets('tapping Серверы tab shows LocationsPage', (tester) async {
    await tester.pumpWidget(_buildShell());

    await tester.tap(find.byIcon(Icons.location_on_rounded));
    await tester.pump();

    expect(find.byType(LocationsPage), findsOneWidget);
  });

  testWidgets('tapping Подписка tab shows SubscriptionPage', (tester) async {
    await tester.pumpWidget(_buildShell());

    await tester.tap(find.byIcon(Icons.workspace_premium_rounded).first);
    await tester.pump();

    expect(find.byType(SubscriptionPage), findsOneWidget);
  });

  testWidgets('tapping Настройки tab shows SettingsPage', (tester) async {
    await tester.pumpWidget(_buildShell());

    await tester.tap(find.byIcon(Icons.settings_rounded));
    await tester.pump();

    expect(find.byType(SettingsPage), findsOneWidget);
  });
}
