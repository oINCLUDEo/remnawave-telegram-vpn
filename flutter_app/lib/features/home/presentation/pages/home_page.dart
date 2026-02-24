import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/theme/app_colors.dart';
import '../cubit/vpn_cubit.dart';
import '../cubit/vpn_state.dart';
import '../widgets/server_card.dart';
import '../widgets/subscription_badge.dart';
import '../widgets/vpn_connect_button.dart';

/// Home / Dashboard screen — the main interaction point of the app.
///
/// Layout (top → bottom):
///   • App bar with logo + subscription badge
///   • Central VPN connect button
///   • VPN status label
///   • Server selection card
///
/// No advertising blocks are placed on this screen intentionally.
class HomePage extends StatelessWidget {
  const HomePage({super.key, this.onOpenLocations});

  /// Called when the user taps the server card to pick a different server.
  final VoidCallback? onOpenLocations;

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => VpnCubit(),
      child: _HomeView(onOpenLocations: onOpenLocations),
    );
  }
}

class _HomeView extends StatelessWidget {
  const _HomeView({this.onOpenLocations});

  final VoidCallback? onOpenLocations;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: _buildAppBar(context),
      body: _buildBody(context),
    );
  }

  PreferredSizeWidget _buildAppBar(BuildContext context) {
    return AppBar(
      backgroundColor: Colors.transparent,
      elevation: 0,
      leadingWidth: 0,
      leading: const SizedBox.shrink(),
      title: Row(
        children: [
          // Logo mark
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppColors.primary, AppColors.accent],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(9),
              boxShadow: [
                BoxShadow(
                  color: AppColors.primary.withValues(alpha: 0.45),
                  blurRadius: 12,
                  spreadRadius: 1,
                ),
              ],
            ),
            child: const Icon(
              Icons.shield_rounded,
              color: Colors.white,
              size: 18,
            ),
          ),
          const SizedBox(width: 10),
          Text(
            'Ulya VPN',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.5,
                ),
          ),
        ],
      ),
      actions: [
        // Subscription badge in top-right area
        const Padding(
          padding: EdgeInsets.only(right: 16),
          child: Center(
            child: SubscriptionBadge(
              // TODO(subscription): replace with data from SubscriptionCubit.
              tier: SubscriptionTier.none,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildBody(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppColors.background,
            AppColors.backgroundDeep,
          ],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        ),
      ),
      child: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 16),

            // Central connect button + status — expands to fill available space.
            Expanded(
              child: _buildConnectSection(context),
            ),

            // Server selection card pinned to the bottom.
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
              child: ServerCard(
                // TODO(server): replace with data from LocationsCubit.
                location: 'Нидерланды, Амстердам',
                flagEmoji: '🇳🇱',
                isOnline: true,
                isRecommended: true,
                onTap: onOpenLocations,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildConnectSection(BuildContext context) {
    return BlocBuilder<VpnCubit, VpnState>(
      builder: (context, state) {
        final statusLabel = switch (state) {
          VpnConnected() => 'Защищено',
          VpnConnecting() => 'Подключение…',
          VpnDisconnecting() => 'Отключение…',
          VpnDisconnected() => 'Отключен',
        };

        final statusColor = switch (state) {
          VpnConnected() => AppColors.success,
          VpnConnecting() || VpnDisconnecting() => AppColors.warning,
          VpnDisconnected() => AppColors.textSecondary,
        };

        return Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const VpnConnectButton(),
            const SizedBox(height: 28),
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              child: Text(
                statusLabel,
                key: ValueKey(statusLabel),
                style: TextStyle(
                  color: statusColor,
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                  letterSpacing: 0.8,
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}
