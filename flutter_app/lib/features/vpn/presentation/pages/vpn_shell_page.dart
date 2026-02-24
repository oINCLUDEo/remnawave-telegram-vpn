import 'dart:ui';
import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import '../widgets/dot_grid_background.dart';
import 'vpn_home_page.dart';
import 'server_selection_page.dart';
import 'subscription_page.dart';

class VpnShellPage extends StatefulWidget {
  const VpnShellPage({super.key});

  @override
  State<VpnShellPage> createState() => _VpnShellPageState();
}

class _VpnShellPageState extends State<VpnShellPage> {
  // Index mapping: 0=Серверы, 1=Premium, 2=VPN(home), 3=Профиль, 4=Настройки
  int _currentIndex = 2; // start on VPN home

  late final PageController _pageController;

  @override
  void initState() {
    super.initState();
    _pageController = PageController(initialPage: 2);
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _navigateTo(int index) {
    setState(() => _currentIndex = index);
    _pageController.animateToPage(
      index,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // PageView enables left/right swipe between tabs.
      body: PageView(
        controller: _pageController,
        onPageChanged: (index) => setState(() => _currentIndex = index),
        children: const [
          ServerSelectionPage(),
          SubscriptionPage(),
          VpnHomePage(),
          _PlaceholderPage(),
          _PlaceholderPage(),
        ],
      ),
      bottomNavigationBar: _buildBottomNav(),
    );
  }

  Widget _buildBottomNav() {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
        child: Container(
          decoration: BoxDecoration(
            color: AppColors.backgroundDark.withValues(alpha: 0.85),
            border: const Border(
              top: BorderSide(color: AppColors.glassBorder, width: 1),
            ),
          ),
          child: SafeArea(
            top: false,
            child: SizedBox(
              height: 64,
              child: Row(
                children: [
                  // Left: Серверы
                  Expanded(
                    child: _NavItem(
                      icon: Icons.language_rounded,
                      label: 'Серверы',
                      isActive: _currentIndex == 0,
                      onTap: () => _navigateTo(0),
                    ),
                  ),
                  // Left: Premium
                  Expanded(
                    child: _NavItem(
                      icon: Icons.workspace_premium_rounded,
                      label: 'Premium',
                      isActive: _currentIndex == 1,
                      onTap: () => _navigateTo(1),
                    ),
                  ),
                  // Center: VPN (wide, prominent)
                  _VpnCenterButton(
                    isActive: _currentIndex == 2,
                    onTap: () => _navigateTo(2),
                  ),
                  // Right: Профиль
                  Expanded(
                    child: _NavItem(
                      icon: Icons.person_outline_rounded,
                      label: 'Профиль',
                      isActive: _currentIndex == 3,
                      onTap: () => _navigateTo(3),
                    ),
                  ),
                  // Right: Настройки
                  Expanded(
                    child: _NavItem(
                      icon: Icons.settings_outlined,
                      label: 'Настройки',
                      isActive: _currentIndex == 4,
                      onTap: () => _navigateTo(4),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ── Centre VPN button ────────────────────────────────────────────────────────

class _VpnCenterButton extends StatelessWidget {
  const _VpnCenterButton({
    required this.isActive,
    required this.onTap,
  });

  final bool isActive;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      // Slightly more horizontal margin than regular items
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 14),
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          // Narrow fixed-width pill — smaller than before
          width: 52,
          decoration: BoxDecoration(
            // Always the same dark background; active state is shown via text color only
            color: const Color(0xFF1C2340),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: isActive
                  ? Colors.white.withValues(alpha: 0.35)
                  : AppColors.glassBorder,
              width: 1,
            ),
          ),
          child: Center(
            child: Text(
              'VPN',
              style: TextStyle(
                // Inactive: muted; active: bright white — no gold
                color: isActive ? Colors.white : AppColors.textSecondary,
                fontSize: 12,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.2,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ── Regular nav item ─────────────────────────────────────────────────────────

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.icon,
    required this.label,
    required this.isActive,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool isActive;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    // Active state: brighter white icon + label, no background box.
    final color = isActive ? Colors.white : AppColors.textSecondary;
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 20, color: color),
          const SizedBox(height: 2),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 10,
              fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Placeholder for not-yet-implemented pages ────────────────────────────────

class _PlaceholderPage extends StatelessWidget {
  const _PlaceholderPage();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.background, AppColors.backgroundDark],
        ),
      ),
      child: DotGridBackground(
        child: const Center(
          child: Text(
            'Скоро',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 18),
          ),
        ),
      ),
    );
  }
}
