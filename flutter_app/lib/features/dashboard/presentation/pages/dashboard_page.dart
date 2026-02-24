import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/di/injection.dart';
import '../../../../core/router/app_router.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../auth/domain/entities/user.dart';
import '../../../auth/presentation/bloc/auth_bloc.dart';
import '../../../auth/presentation/bloc/auth_event.dart';
import '../../../auth/presentation/bloc/auth_state.dart';
import '../../../profile/presentation/pages/profile_page.dart';
import '../../../settings/presentation/pages/settings_page.dart';
import '../../../subscription/presentation/bloc/subscription_bloc.dart';
import '../../../subscription/presentation/bloc/subscription_event.dart';
import '../../../subscription/presentation/bloc/subscription_state.dart';
import '../../../subscription/presentation/pages/subscription_page.dart';
import '../../../subscription/presentation/widgets/subscription_status_card.dart';

/// Main shell screen with bottom navigation.
class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    return MultiBlocProvider(
      providers: [
        BlocProvider<AuthBloc>(
          create: (_) =>
              sl<AuthBloc>()..add(const LoadProfileRequested()),
        ),
        BlocProvider<SubscriptionBloc>(
          create: (_) =>
              sl<SubscriptionBloc>()..add(const SubscriptionLoadRequested()),
        ),
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
              ProfilePage(),
              SettingsPage(),
            ],
          ),
          bottomNavigationBar: NavigationBar(
            selectedIndex: _currentIndex,
            onDestinationSelected: (i) => setState(() => _currentIndex = i),
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
                icon: Icon(Icons.shield_outlined),
                selectedIcon: Icon(Icons.shield_rounded),
                label: 'Подписка',
              ),
              NavigationDestination(
                icon: Icon(Icons.person_outline_rounded),
                selectedIcon: Icon(Icons.person_rounded),
                label: 'Профиль',
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

  /// Navigate to a specific tab by index.
  void navigateTo(int index) => setState(() => _currentIndex = index);
}

/// Home tab — user summary + subscription overview.
class _HomeTab extends StatelessWidget {
  const _HomeTab();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
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
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 16),
                _buildHeader(context),
                const SizedBox(height: 24),
                _buildSubscriptionSection(context),
                const SizedBox(height: 24),
                _buildQuickStats(context),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    final theme = Theme.of(context);
    return BlocBuilder<AuthBloc, AuthState>(
      builder: (context, state) {
        String greeting = 'Добро пожаловать!';
        String subtitle = 'Ulya VPN';
        User? user;

        if (state is AuthProfileLoaded) {
          user = state.user;
          final name =
              user.firstName ?? user.username ?? user.email?.split('@').first;
          if (name != null) greeting = 'Привет, $name!';
          subtitle = user.email ?? 'Ulya VPN';
        }

        return Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [AppColors.primary, AppColors.accent],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Icon(
                Icons.shield_rounded,
                color: Colors.white,
                size: 26,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(greeting, style: theme.textTheme.titleLarge),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: theme.textTheme.bodyMedium,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            if (user != null) _BalanceBadge(balanceRubles: user.balanceRubles),
          ],
        );
      },
    );
  }

  Widget _buildSubscriptionSection(BuildContext context) {
    return BlocBuilder<SubscriptionBloc, SubscriptionState>(
      builder: (context, state) {
        if (state is SubscriptionLoading || state is SubscriptionInitial) {
          return const _SectionShimmer();
        }
        if (state is SubscriptionError) {
          return _SectionError(
            message: state.message,
            onRetry: () => context
                .read<SubscriptionBloc>()
                .add(const SubscriptionLoadRequested()),
          );
        }
        if (state is SubscriptionLoaded) {
          if (state.subscription == null) {
            return _NoSubscriptionCard(
              onBuy: () => _navigateToSubscription(context),
            );
          }
          return SubscriptionStatusCard(
            subscription: state.subscription!,
            onManage: () => _navigateToSubscription(context),
          );
        }
        return const SizedBox.shrink();
      },
    );
  }

  void _navigateToSubscription(BuildContext context) {
    context
        .findAncestorStateOfType<_DashboardPageState>()
        ?.navigateTo(1);
  }

  Widget _buildQuickStats(BuildContext context) {
    final theme = Theme.of(context);
    return BlocBuilder<SubscriptionBloc, SubscriptionState>(
      builder: (context, state) {
        if (state is! SubscriptionLoaded || state.subscription == null) {
          return const SizedBox.shrink();
        }
        final sub = state.subscription!;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Статистика', style: theme.textTheme.titleLarge),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _StatCard(
                    icon: Icons.devices_rounded,
                    label: 'Устройств',
                    value: '${sub.deviceLimit}',
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _StatCard(
                    icon: Icons.dns_rounded,
                    label: 'Серверов',
                    value: '${sub.servers.length}',
                  ),
                ),
              ],
            ),
          ],
        );
      },
    );
  }
}

// ─────────────────────────────────── Shared widgets ───────────────────────────────────

class _BalanceBadge extends StatelessWidget {
  const _BalanceBadge({required this.balanceRubles});

  final double balanceRubles;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.divider),
      ),
      child: Text(
        '${balanceRubles.toStringAsFixed(0)} ₽',
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: AppColors.accent,
              fontSize: 13,
            ),
      ),
    );
  }
}

class _NoSubscriptionCard extends StatelessWidget {
  const _NoSubscriptionCard({this.onBuy});

  final VoidCallback? onBuy;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        children: [
          const Icon(
            Icons.shield_outlined,
            size: 52,
            color: AppColors.textHint,
          ),
          const SizedBox(height: 14),
          Text(
            'Нет активной подписки',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 6),
          Text(
            'Подключите VPN и получите доступ ко всем серверам.',
            style: theme.textTheme.bodyMedium,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: onBuy,
              child: const Text('Выбрать план'),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionShimmer extends StatelessWidget {
  const _SectionShimmer();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 180,
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(20),
      ),
      child: const Center(
        child: CircularProgressIndicator(color: AppColors.primary),
      ),
    );
  }
}

class _SectionError extends StatelessWidget {
  const _SectionError({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
      ),
      child: Column(
        children: [
          const Icon(Icons.error_outline_rounded,
              color: AppColors.error, size: 40),
          const SizedBox(height: 8),
          Text(
            message,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          TextButton(onPressed: onRetry, child: const Text('Повторить')),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: AppColors.primary, size: 22),
          const SizedBox(height: 10),
          Text(value, style: theme.textTheme.headlineMedium),
          const SizedBox(height: 2),
          Text(label, style: theme.textTheme.bodyMedium),
        ],
      ),
    );
  }
}
