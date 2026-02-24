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

/// Main shell — bottom navigation with 4 tabs.
class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  int _currentIndex = 0;

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
          body: IndexedStack(
            index: _currentIndex,
            children: const [
              _HomeTab(),
              SubscriptionPage(),
              LocationsPage(),
              SettingsPage(),
            ],
          ),
          bottomNavigationBar: NavigationBar(
            selectedIndex: _currentIndex,
            onDestinationSelected: navigateTo,
            backgroundColor: AppColors.surface,
            indicatorColor: AppColors.primary.withValues(alpha: 0.18),
            labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
            destinations: const [
              NavigationDestination(
                icon: Icon(Icons.home_outlined),
                selectedIcon: Icon(Icons.home_rounded),
                label: 'Главная',
              ),
              NavigationDestination(
                icon: Icon(Icons.credit_card_outlined),
                selectedIcon: Icon(Icons.credit_card_rounded),
                label: 'Подписка',
              ),
              NavigationDestination(
                icon: Icon(Icons.public_outlined),
                selectedIcon: Icon(Icons.public_rounded),
                label: 'Серверы',
              ),
              NavigationDestination(
                icon: Icon(Icons.settings_outlined),
                selectedIcon: Icon(Icons.settings_rounded),
                label: 'Настройки',
              ),
            ],
          ),
        ),
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
  /// Local VPN toggle state — will be wired to a real VPN service later.
  bool _vpnConnected = false;

  void _toggleVpn() => setState(() => _vpnConnected = !_vpnConnected);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
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
            child: Column(
              children: [
                _TopBar(vpnConnected: _vpnConnected),
                _VpnSection(
                  vpnConnected: _vpnConnected,
                  onToggle: _toggleVpn,
                ),
                const _PremiumBenefits(),
                const SizedBox(height: 16),
                _ServerBox(
                  onTap: () => context
                      .findAncestorStateOfType<_DashboardPageState>()
                      ?.navigateTo(2),
                ),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Top bar: app name + subscription badge
// ─────────────────────────────────────────────────────────────────────────────

class _TopBar extends StatelessWidget {
  const _TopBar({required this.vpnConnected});

  final bool vpnConnected;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
      child: Row(
        children: [
          // Logo
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppColors.primary, AppColors.accent],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.shield_rounded, color: Colors.white, size: 20),
          ),
          const SizedBox(width: 10),
          Text(
            'Ulya VPN',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
          const Spacer(),
          // Subscription badge
          BlocBuilder<SubscriptionBloc, SubscriptionState>(
            builder: (context, state) {
              if (state is SubscriptionLoaded) {
                return _SubscriptionBadge(subscription: state.subscription);
              }
              return const SizedBox.shrink();
            },
          ),
        ],
      ),
    );
  }
}

class _SubscriptionBadge extends StatelessWidget {
  const _SubscriptionBadge({required this.subscription});

  final Subscription? subscription;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (subscription == null || subscription!.isExpired) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: AppColors.surfaceVariant,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.divider),
        ),
        child: Text(
          'Нет подписки',
          style: theme.textTheme.labelSmall?.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
      );
    }

    final sub = subscription!;
    final label = sub.tariffName ?? 'Премиум';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppColors.primary, AppColors.accent],
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
        ),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.verified_rounded, size: 12, color: Colors.white),
          const SizedBox(width: 4),
          Text(
            label,
            style: theme.textTheme.labelSmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Central VPN button + status
// ─────────────────────────────────────────────────────────────────────────────

class _VpnSection extends StatelessWidget {
  const _VpnSection({
    required this.vpnConnected,
    required this.onToggle,
  });

  final bool vpnConnected;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 40),
      child: Column(
        children: [
          // Subscription status sub-line
          BlocBuilder<SubscriptionBloc, SubscriptionState>(
            builder: (context, state) {
              if (state is SubscriptionLoaded && state.subscription != null) {
                final sub = state.subscription!;
                final label = sub.isExpired
                    ? 'Подписка истекла'
                    : 'Активна до ${_fmtDate(sub.endDate)}';
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Text(
                    label,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: sub.isExpired
                          ? AppColors.error
                          : AppColors.textSecondary,
                    ),
                  ),
                );
              }
              return const SizedBox(height: 12);
            },
          ),

          // Big circle button
          GestureDetector(
            onTap: onToggle,
            child: _VpnButton(connected: vpnConnected),
          ),

          const SizedBox(height: 20),

          // Status label
          Text(
            vpnConnected ? 'VPN подключен' : 'VPN отключен',
            style: theme.textTheme.titleMedium?.copyWith(
              color: vpnConnected ? AppColors.success : AppColors.textSecondary,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  String _fmtDate(DateTime d) =>
      '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')}.${d.year}';
}

class _VpnButton extends StatelessWidget {
  const _VpnButton({required this.connected});

  final bool connected;

  @override
  Widget build(BuildContext context) {
    // Outer glow ring
    return Container(
      width: 160,
      height: 160,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(
          color: connected
              ? AppColors.success.withValues(alpha: 0.25)
              : AppColors.primary.withValues(alpha: 0.15),
          width: 12,
        ),
      ),
      child: Container(
        margin: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: connected
              ? const LinearGradient(
                  colors: [Color(0xFF00C896), Color(0xFF00A878)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : const LinearGradient(
                  colors: [AppColors.primary, AppColors.primaryDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
          boxShadow: [
            BoxShadow(
              color: connected
                  ? AppColors.success.withValues(alpha: 0.4)
                  : AppColors.primary.withValues(alpha: 0.4),
              blurRadius: 30,
              spreadRadius: 2,
            ),
          ],
        ),
        child: const Icon(
          Icons.power_settings_new_rounded,
          size: 52,
          color: Colors.white,
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Premium benefits list
// ─────────────────────────────────────────────────────────────────────────────

class _PremiumBenefits extends StatelessWidget {
  const _PremiumBenefits();

  static const _items = [
    _Benefit(icon: Icons.play_circle_outline_rounded, label: 'YouTube без рекламы'),
    _Benefit(icon: Icons.list_alt_rounded, label: 'Белые списки сайтов'),
    _Benefit(icon: Icons.devices_rounded, label: 'Любые устройства'),
    _Benefit(icon: Icons.speed_rounded, label: 'Без ограничений скорости'),
    _Benefit(icon: Icons.security_rounded, label: 'Защита трафика'),
  ];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppColors.divider),
        ),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.star_rounded,
                    size: 16, color: AppColors.warning),
                const SizedBox(width: 6),
                Text(
                  'Преимущества Ulya VPN',
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: AppColors.textSecondary,
                    fontSize: 12,
                    letterSpacing: 0.6,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ..._items.map((b) => _BenefitRow(benefit: b)),
          ],
        ),
      ),
    );
  }
}

class _Benefit {
  const _Benefit({required this.icon, required this.label});
  final IconData icon;
  final String label;
}

class _BenefitRow extends StatelessWidget {
  const _BenefitRow({required this.benefit});

  final _Benefit benefit;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(benefit.icon, size: 15, color: AppColors.primary),
          ),
          const SizedBox(width: 10),
          Text(
            benefit.label,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const Spacer(),
          const Icon(Icons.check_rounded,
              size: 15, color: AppColors.success),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Server selector box
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
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 20),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.card,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: AppColors.divider),
            ),
            child: Row(
              children: [
                // Country flag / icon
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: AppColors.surfaceVariant,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Center(
                    child: Text(
                      server != null
                          ? _flagEmoji(server.countryCode)
                          : '🌍',
                      style: const TextStyle(fontSize: 22),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        server?.name ?? 'Автоматически',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Row(
                        children: [
                          Container(
                            width: 6,
                            height: 6,
                            decoration: const BoxDecoration(
                              color: AppColors.success,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            'Online',
                            style:
                                Theme.of(context).textTheme.bodySmall?.copyWith(
                                      color: AppColors.success,
                                    ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const Icon(
                  Icons.chevron_right_rounded,
                  color: AppColors.textHint,
                  size: 20,
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  String _flagEmoji(String? countryCode) {
    if (countryCode == null || countryCode.length != 2) return '🌍';
    final base = 127397;
    final code = countryCode.toUpperCase().codeUnits;
    return String.fromCharCode(base + code[0]) +
        String.fromCharCode(base + code[1]);
  }
}
