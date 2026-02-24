import 'dart:ui';

import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import 'home_page.dart';
import 'locations_page.dart';
import 'settings_page.dart';
import 'subscription_page.dart';

/// Root scaffold that hosts the four main tabs with a premium bottom navigation
/// bar. The Home tab is visually centred and elevated.
class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _currentIndex = 1; // Start on Home (index 1 of 4 tabs)

  static const _tabs = [
    _Tab(icon: Icons.workspace_premium_rounded, label: 'Подписка'),
    _Tab(icon: Icons.shield_rounded, label: 'Главная'), // centre
    _Tab(icon: Icons.location_on_rounded, label: 'Серверы'),
    _Tab(icon: Icons.settings_rounded, label: 'Настройки'),
  ];

  late final _pages = <Widget>[
    const SubscriptionPage(),
    HomePage(onOpenLocations: () => setState(() => _currentIndex = 2)),
    const LocationsPage(),
    const SettingsPage(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _pages,
      ),
      extendBody: true,
      bottomNavigationBar: _PremiumNavBar(
        currentIndex: _currentIndex,
        tabs: _tabs,
        onTap: (i) => setState(() => _currentIndex = i),
      ),
    );
  }
}

class _Tab {
  const _Tab({required this.icon, required this.label});
  final IconData icon;
  final String label;
}

/// Frosted-glass bottom navigation bar with a floating centre Home tab.
class _PremiumNavBar extends StatelessWidget {
  const _PremiumNavBar({
    required this.currentIndex,
    required this.tabs,
    required this.onTap,
  });

  final int currentIndex;
  final List<_Tab> tabs;
  final ValueChanged<int> onTap;

  // Index of the centre (Home) tab.
  static const int _centreIndex = 1;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(28),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
          child: Container(
            height: 68,
            decoration: BoxDecoration(
              color: AppColors.glassBackground.withValues(alpha: 0.55),
              borderRadius: BorderRadius.circular(28),
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.12),
                width: 1,
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: List.generate(tabs.length, (i) {
                final isCentre = i == _centreIndex;
                final isSelected = currentIndex == i;
                return _NavItem(
                  tab: tabs[i],
                  isSelected: isSelected,
                  isCentre: isCentre,
                  onTap: () => onTap(i),
                );
              }),
            ),
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.tab,
    required this.isSelected,
    required this.isCentre,
    required this.onTap,
  });

  final _Tab tab;
  final bool isSelected;
  final bool isCentre;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    if (isCentre) return _CentreNavItem(tab: tab, isSelected: isSelected, onTap: onTap);

    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: SizedBox(
        width: 68,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              tab.icon,
              size: 22,
              color: isSelected ? AppColors.primary : AppColors.textSecondary,
            ),
            const SizedBox(height: 4),
            Text(
              tab.label,
              style: TextStyle(
                fontSize: 10,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                color: isSelected ? AppColors.primary : AppColors.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// The elevated centre (Home) button in the nav bar.
class _CentreNavItem extends StatelessWidget {
  const _CentreNavItem({
    required this.tab,
    required this.isSelected,
    required this.onTap,
  });

  final _Tab tab;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: const LinearGradient(
                colors: [AppColors.primary, AppColors.primaryDark],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              boxShadow: [
                BoxShadow(
                  color: AppColors.primary.withValues(alpha: isSelected ? 0.6 : 0.3),
                  blurRadius: isSelected ? 20 : 10,
                  spreadRadius: isSelected ? 3 : 0,
                ),
              ],
            ),
            child: Icon(
              tab.icon,
              size: 26,
              color: Colors.white.withValues(alpha: isSelected ? 1.0 : 0.8),
            ),
          ),
        ],
      ),
    );
  }
}
