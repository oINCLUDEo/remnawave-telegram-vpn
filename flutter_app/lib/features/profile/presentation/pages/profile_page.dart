import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../auth/presentation/bloc/auth_bloc.dart';
import '../../../auth/presentation/bloc/auth_event.dart';
import '../../../auth/presentation/bloc/auth_state.dart';

/// User profile screen.
class ProfilePage extends StatelessWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Профиль')),
      body: BlocBuilder<AuthBloc, AuthState>(
        builder: (context, state) {
          if (state is AuthProfileLoaded) {
            final user = state.user;
            final displayName = user.firstName != null && user.lastName != null
                ? '${user.firstName} ${user.lastName}'
                : user.firstName ?? user.username ?? 'Пользователь';
            return SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  const SizedBox(height: 8),
                  _Avatar(name: displayName),
                  const SizedBox(height: 16),
                  Text(displayName, style: theme.textTheme.headlineMedium),
                  if (user.email != null) ...[
                    const SizedBox(height: 4),
                    Text(user.email!, style: theme.textTheme.bodyMedium),
                  ],
                  const SizedBox(height: 32),
                  _InfoCard(
                    items: [
                      _InfoItem(
                        icon: Icons.account_balance_wallet_outlined,
                        label: 'Баланс',
                        value:
                            '${user.balanceRubles.toStringAsFixed(2)} ₽',
                      ),
                      if (user.referralCode != null)
                        _InfoItem(
                          icon: Icons.share_outlined,
                          label: 'Реферальный код',
                          value: user.referralCode!,
                        ),
                      _InfoItem(
                        icon: Icons.verified_user_outlined,
                        label: 'Email подтверждён',
                        value: user.emailVerified ? 'Да' : 'Нет',
                        valueColor: user.emailVerified
                            ? AppColors.success
                            : AppColors.warning,
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      icon: const Icon(Icons.logout_rounded,
                          color: AppColors.error),
                      label: const Text(
                        'Выйти',
                        style: TextStyle(color: AppColors.error),
                      ),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: AppColors.error),
                        minimumSize: const Size(double.infinity, 50),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                      ),
                      onPressed: () =>
                          context.read<AuthBloc>().add(const LogoutRequested()),
                    ),
                  ),
                ],
              ),
            );
          }
          if (state is AuthLoading) {
            return const Center(
              child: CircularProgressIndicator(color: AppColors.primary),
            );
          }
          return Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.person_outline_rounded,
                    size: 64, color: AppColors.textHint),
                const SizedBox(height: 16),
                Text('Профиль недоступен',
                    style: theme.textTheme.bodyMedium),
                const SizedBox(height: 12),
                TextButton(
                  onPressed: () => context
                      .read<AuthBloc>()
                      .add(const LoadProfileRequested()),
                  child: const Text('Обновить'),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _Avatar extends StatelessWidget {
  const _Avatar({required this.name});

  final String name;

  @override
  Widget build(BuildContext context) {
    final initials =
        name.trim().split(' ').map((w) => w.isNotEmpty ? w[0] : '').take(2).join().toUpperCase();
    return Container(
      width: 80,
      height: 80,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppColors.primary, AppColors.accent],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        shape: BoxShape.circle,
      ),
      child: Center(
        child: Text(
          initials.isEmpty ? '?' : initials,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 28,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.items});

  final List<_InfoItem> items;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        children: [
          for (int i = 0; i < items.length; i++) ...[
            items[i],
            if (i < items.length - 1)
              const Divider(height: 1, indent: 16, endIndent: 16),
          ],
        ],
      ),
    );
  }
}

class _InfoItem extends StatelessWidget {
  const _InfoItem({
    required this.icon,
    required this.label,
    required this.value,
    this.valueColor,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        children: [
          Icon(icon, color: AppColors.primary, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(label, style: theme.textTheme.bodyMedium),
          ),
          Text(
            value,
            style: theme.textTheme.labelLarge?.copyWith(
              color: valueColor ?? AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}
