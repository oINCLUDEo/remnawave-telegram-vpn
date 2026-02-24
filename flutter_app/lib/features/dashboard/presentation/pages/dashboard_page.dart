import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/di/injection.dart';
import '../../../../core/router/app_router.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../auth/presentation/bloc/auth_bloc.dart';
import '../../../auth/presentation/bloc/auth_event.dart';
import '../../../auth/presentation/bloc/auth_state.dart';
import '../../../locations/presentation/pages/locations_page.dart';
import '../../../settings/presentation/pages/settings_page.dart';
import '../../../subscription/domain/entities/server_info.dart';
import '../../../subscription/domain/entities/subscription.dart';
import '../../../subscription/presentation/bloc/subscription_bloc.dart';
import '../../../subscription/presentation/bloc/subscription_event.dart';
import '../../../subscription/presentation/bloc/subscription_state.dart';
import '../../../subscription/presentation/pages/subscription_page.dart';

// ─────────────────────────────────────────────────────────────────────────────
// Shell
// ─────────────────────────────────────────────────────────────────────────────

/// Main app shell — floating glass navigation + 4 tab pages.
class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  // Tab order: 0=Subscription 1=Locations 2=Home 3=Settings
  // Home is index 2 — the centre item that is visually elevated.
  int _currentIndex = 2;

  late final AuthBloc _authBloc;
  late final SubscriptionBloc _subscriptionBloc;

  @override
  void initState() {
    super.initState();
    _authBloc = sl<AuthBloc>();
    _subscriptionBloc = sl<SubscriptionBloc>();
    _authBloc.add(const LoadProfileRequested());
    _subscriptionBloc.add(const SubscriptionLoadRequested());
  }

  @override
  void dispose() {
    _authBloc.close();
    _subscriptionBloc.close();
    super.dispose();
  }

  void navigateTo(int index) => setState(() => _currentIndex = index);

  @override
  Widget build(BuildContext context) {
    return MultiBlocProvider(
      providers: [
        BlocProvider<AuthBloc>.value(value: _authBloc),
        BlocProvider<SubscriptionBloc>.value(value: _subscriptionBloc),
      ],
      child: BlocListener<AuthBloc, AuthState>(
        listener: (context, state) {
          if (state is AuthLoggedOut) {
            context.go(AppRoutes.login);
          }
        },
        child: Scaffold(
          extendBody: true, // body renders behind the floating nav bar
          backgroundColor: AppColors.background,
          body: IndexedStack(
            index: _currentIndex,
            children: const [
              SubscriptionPage(),
              LocationsPage(),
              _HomeTab(),
              SettingsPage(),
            ],
          ),
          bottomNavigationBar: _GlassNavBar(
            currentIndex: _currentIndex,
            onTabSelected: navigateTo,
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Glass floating navigation bar
// ─────────────────────────────────────────────────────────────────────────────

class _GlassNavBar extends StatelessWidget {
  const _GlassNavBar({
    required this.currentIndex,
    required this.onTabSelected,
  });

  final int currentIndex;
  final void Function(int) onTabSelected;

  // ── items left/right of the Home button ──────────────────────────────────

  static const _leftItems = [
    _NavItemData(0, Icons.credit_card_outlined, Icons.credit_card_rounded, 'Подписка'),
    _NavItemData(1, Icons.public_outlined, Icons.public_rounded, 'Серверы'),
  ];
  static const _rightItems = [
    _NavItemData(3, Icons.settings_outlined, Icons.settings_rounded, 'Настройки'),
  ];

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
        child: SizedBox(
          height: 80,
          child: Stack(
            clipBehavior: Clip.none,
            alignment: Alignment.bottomCenter,
            children: [
              // ── glass bar ─────────────────────────────────────────────────
              Positioned(
                bottom: 0,
                left: 0,
                right: 0,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(32),
                  child: BackdropFilter(
                    filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
                    child: Container(
                      height: 64,
                      decoration: BoxDecoration(
                        color: AppColors.glassDark,
                        borderRadius: BorderRadius.circular(32),
                        border: Border.all(
                          color: AppColors.glassBorder,
                          width: 1,
                        ),
                      ),
                      child: Row(
                        children: [
                          // Left items
                          ..._leftItems.map(
                            (d) => Expanded(
                              child: _SideNavItem(
                                data: d,
                                selected: currentIndex == d.index,
                                onTap: () => onTabSelected(d.index),
                              ),
                            ),
                          ),
                          // Centre gap for elevated home button
                          const SizedBox(width: 72),
                          // Right items
                          ..._rightItems.map(
                            (d) => Expanded(
                              child: _SideNavItem(
                                data: d,
                                selected: currentIndex == d.index,
                                onTap: () => onTabSelected(d.index),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

              // ── elevated Home button ──────────────────────────────────────
              Positioned(
                bottom: 10,
                child: GestureDetector(
                  onTap: () => onTabSelected(2),
                  child: _HomeNavButton(selected: currentIndex == 2),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavItemData {
  const _NavItemData(this.index, this.icon, this.selectedIcon, this.label);
  final int index;
  final IconData icon;
  final IconData selectedIcon;
  final String label;
}

class _SideNavItem extends StatelessWidget {
  const _SideNavItem({
    required this.data,
    required this.selected,
    required this.onTap,
  });

  final _NavItemData data;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            selected ? data.selectedIcon : data.icon,
            size: 22,
            color: selected ? AppColors.primary : AppColors.textHint,
          ),
          const SizedBox(height: 3),
          Text(
            data.label,
            style: TextStyle(
              fontSize: 10,
              fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
              color: selected ? AppColors.primary : AppColors.textHint,
            ),
          ),
        ],
      ),
    );
  }
}

class _HomeNavButton extends StatelessWidget {
  const _HomeNavButton({required this.selected});

  final bool selected;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 56,
      height: 56,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: selected
            ? const LinearGradient(
                colors: [AppColors.primary, AppColors.primaryDark],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              )
            : LinearGradient(
                colors: [
                  AppColors.surfaceVariant,
                  AppColors.surface,
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withValues(alpha: selected ? 0.45 : 0.15),
            blurRadius: selected ? 16 : 8,
            spreadRadius: selected ? 1 : 0,
          ),
        ],
        border: Border.all(
          color: AppColors.glassBorder,
          width: 1,
        ),
      ),
      child: Icon(
        Icons.home_rounded,
        size: 26,
        color: selected ? Colors.white : AppColors.textSecondary,
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Home tab
// ─────────────────────────────────────────────────────────────────────────────

class _HomeTab extends StatefulWidget {
  const _HomeTab();

  @override
  State<_HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<_HomeTab> {
  bool _vpnConnected = false;

  void _toggleVpn() => setState(() => _vpnConnected = !_vpnConnected);

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);

    return Stack(
      children: [
        // ── deep space gradient background ─────────────────────────────────
        Positioned.fill(
          child: Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0xFF0A0A18),
                  Color(0xFF130E28),
                  Color(0xFF0A0A18),
                ],
                stops: [0, 0.5, 1],
              ),
            ),
          ),
        ),

        // ── radial glow behind VPN button ───────────────────────────────────
        Positioned(
          top: size.height * 0.22,
          left: size.width * 0.5 - 140,
          child: _RadialGlow(
            color: _vpnConnected ? AppColors.success : AppColors.primary,
          ),
        ),

        // ── main content ────────────────────────────────────────────────────
        SafeArea(
          bottom: false,
          child: RefreshIndicator(
            color: AppColors.primary,
            onRefresh: () async {
              context.read<AuthBloc>().add(const LoadProfileRequested());
              context
                  .read<SubscriptionBloc>()
                  .add(const SubscriptionRefreshRequested());
            },
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              child: SizedBox(
                // Ensure enough height to fill screen so pull-to-refresh works
                height: size.height,
                child: Column(
                  children: [
                    const SizedBox(height: 8),
                    _TopBar(),
                    const SizedBox(height: 4),
                    _SubscriptionStatusLine(),
                    const Spacer(),
                    _VpnSection(
                      vpnConnected: _vpnConnected,
                      onToggle: _toggleVpn,
                    ),
                    const Spacer(),
                    _ServerBox(
                      onTap: () => context
                          .findAncestorStateOfType<_DashboardPageState>()
                          ?.navigateTo(1),
                    ),
                    // Extra bottom padding for floating nav bar
                    const SizedBox(height: 100),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Background radial glow
// ─────────────────────────────────────────────────────────────────────────────

class _RadialGlow extends StatelessWidget {
  const _RadialGlow({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 280,
      height: 280,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            color.withValues(alpha: 0.18),
            color.withValues(alpha: 0.06),
            Colors.transparent,
          ],
          stops: const [0, 0.5, 1],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Top bar
// ─────────────────────────────────────────────────────────────────────────────

class _TopBar extends StatelessWidget {
  const _TopBar();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Row(
        children: [
          // Logo
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppColors.primary, AppColors.accent],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.shield_rounded, color: Colors.white, size: 18),
          ),
          const SizedBox(width: 10),
          Text(
            'Ulya VPN',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w700,
              letterSpacing: 0.3,
            ),
          ),
          const Spacer(),
          // Subscription badge (glass style)
          BlocBuilder<SubscriptionBloc, SubscriptionState>(
            builder: (context, state) {
              if (state is SubscriptionLoaded) {
                return _GlassSubscriptionBadge(subscription: state.subscription);
              }
              return const SizedBox.shrink();
            },
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Subscription badge – glass style
// ─────────────────────────────────────────────────────────────────────────────

class _GlassSubscriptionBadge extends StatelessWidget {
  const _GlassSubscriptionBadge({required this.subscription});

  final Subscription? subscription;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (subscription == null || subscription!.isExpired) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
            decoration: BoxDecoration(
              color: AppColors.glassWhite,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.glassBorder),
            ),
            child: Text(
              'Нет подписки',
              style: theme.textTheme.labelSmall?.copyWith(
                color: AppColors.textSecondary,
                fontSize: 11,
              ),
            ),
          ),
        ),
      );
    }

    final sub = subscription!;
    final label = sub.tariffName ?? 'Премиум';
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                AppColors.primary.withValues(alpha: 0.35),
                AppColors.accent.withValues(alpha: 0.25),
              ],
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
            ),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: AppColors.primary.withValues(alpha: 0.4),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.verified_rounded, size: 11, color: AppColors.primaryLight),
              const SizedBox(width: 4),
              Text(
                label,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: AppColors.primaryLight,
                  fontWeight: FontWeight.w600,
                  fontSize: 11,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Subscription status line (below top bar)
// ─────────────────────────────────────────────────────────────────────────────

class _SubscriptionStatusLine extends StatelessWidget {
  const _SubscriptionStatusLine();

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<SubscriptionBloc, SubscriptionState>(
      builder: (context, state) {
        if (state is! SubscriptionLoaded || state.subscription == null) {
          return const SizedBox.shrink();
        }
        final sub = state.subscription!;
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Align(
            alignment: Alignment.centerRight,
            child: Text(
              sub.isExpired
                  ? 'Подписка истекла'
                  : 'Активна до ${_fmtDate(sub.endDate)}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: sub.isExpired
                        ? AppColors.error.withValues(alpha: 0.8)
                        : AppColors.textHint,
                    fontSize: 11,
                  ),
            ),
          ),
        );
      },
    );
  }

  String _fmtDate(DateTime d) =>
      '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')}.${d.year}';
}

// ─────────────────────────────────────────────────────────────────────────────
// Central VPN section
// ─────────────────────────────────────────────────────────────────────────────

class _VpnSection extends StatelessWidget {
  const _VpnSection({required this.vpnConnected, required this.onToggle});

  final bool vpnConnected;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      children: [
        GestureDetector(
          onTap: onToggle,
          child: _GlassVpnButton(connected: vpnConnected),
        ),
        const SizedBox(height: 22),
        Text(
          vpnConnected ? 'Защищено' : 'Отключен',
          style: theme.textTheme.titleMedium?.copyWith(
            color: vpnConnected ? AppColors.success : AppColors.textSecondary,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.0,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          vpnConnected
              ? 'Ваш трафик зашифрован'
              : 'Нажмите для подключения',
          style: theme.textTheme.bodySmall?.copyWith(
            color: AppColors.textHint,
            fontSize: 12,
          ),
        ),
      ],
    );
  }
}

class _GlassVpnButton extends StatelessWidget {
  const _GlassVpnButton({required this.connected});

  final bool connected;

  // Colour scheme for each state
  Color get _innerA =>
      connected ? const Color(0xFF00C896) : const Color(0xFF6C63FF);
  Color get _innerB =>
      connected ? const Color(0xFF007A5E) : const Color(0xFF4B44CC);
  Color get _glowColor =>
      connected ? AppColors.success : AppColors.primary;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 200,
      height: 200,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Outermost ring (lowest opacity)
          _ring(200, _glowColor.withValues(alpha: 0.08)),
          // Middle ring
          _ring(168, _glowColor.withValues(alpha: 0.12)),
          // Inner ring
          _ring(140, _glowColor.withValues(alpha: 0.18)),

          // Glass button core
          ClipOval(
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
              child: Container(
                width: 118,
                height: 118,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [_innerA, _innerB],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: _glowColor.withValues(alpha: 0.5),
                      blurRadius: 28,
                      spreadRadius: 2,
                    ),
                  ],
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.15),
                    width: 1.5,
                  ),
                ),
                child: const Icon(
                  Icons.power_settings_new_rounded,
                  size: 46,
                  color: Colors.white,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _ring(double size, Color color) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: color, width: 1),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Glass server selector card
// ─────────────────────────────────────────────────────────────────────────────

class _ServerBox extends StatelessWidget {
  const _ServerBox({this.onTap});

  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<SubscriptionBloc, SubscriptionState>(
      builder: (context, state) {
        ServerInfo? server;
        if (state is SubscriptionLoaded &&
            state.subscription != null &&
            state.subscription!.servers.isNotEmpty) {
          server = state.subscription!.servers.first;
        }

        return GestureDetector(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(22),
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.glassWhite,
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(
                      color: AppColors.glassBorder,
                    ),
                  ),
                  child: Row(
                    children: [
                      // Flag icon
                      Container(
                        width: 46,
                        height: 46,
                        decoration: BoxDecoration(
                          color: AppColors.surfaceVariant.withValues(alpha: 0.6),
                          borderRadius: BorderRadius.circular(13),
                          border: Border.all(
                            color: AppColors.glassBorder,
                          ),
                        ),
                        child: Center(
                          child: Text(
                            server != null
                                ? _flag(server.countryCode)
                                : '🌍',
                            style: const TextStyle(fontSize: 24),
                          ),
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              server?.name ?? 'Автоматически',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(fontWeight: FontWeight.w600),
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 4),
                            Row(
                              children: [
                                Container(
                                  width: 6,
                                  height: 6,
                                  decoration: const BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: AppColors.success,
                                  ),
                                ),
                                const SizedBox(width: 5),
                                Text(
                                  'Online',
                                  style: Theme.of(context)
                                      .textTheme
                                      .bodySmall
                                      ?.copyWith(
                                          color: AppColors.success,
                                          fontSize: 12),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                      Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          color: AppColors.primary.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: AppColors.primary.withValues(alpha: 0.2),
                          ),
                        ),
                        child: const Icon(
                          Icons.chevron_right_rounded,
                          color: AppColors.primary,
                          size: 18,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  String _flag(String? code) {
    if (code == null || code.length != 2) return '🌍';
    const base = 127397;
    final u = code.toUpperCase().codeUnits;
    return String.fromCharCode(base + u[0]) + String.fromCharCode(base + u[1]);
  }
}
