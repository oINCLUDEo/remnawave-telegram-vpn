import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../auth/presentation/bloc/auth_bloc.dart';
import '../../../auth/presentation/bloc/auth_event.dart';
import '../../../auth/presentation/bloc/auth_state.dart';

/// App settings screen (placeholder — full implementation in future sprints).
class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Настройки')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // Profile summary
          BlocBuilder<AuthBloc, AuthState>(
            builder: (context, state) {
              if (state is AuthProfileLoaded) {
                final user = state.user;
                final name = user.firstName ?? user.username ??
                    user.email?.split('@').first ?? 'Пользователь';
                return _ProfileCard(
                  name: name,
                  email: user.email,
                  balanceRubles: user.balanceRubles,
                );
              }
              return const SizedBox.shrink();
            },
          ),
          const SizedBox(height: 20),
          _SettingsSection(
            title: 'Приложение',
            items: [
              _SettingsTile(
                icon: Icons.language_rounded,
                label: 'Язык',
                trailing: const Text('Русский',
                    style: TextStyle(color: AppColors.textSecondary)),
                onTap: () => _showComingSoon(context),
              ),
              _SettingsTile(
                icon: Icons.notifications_outlined,
                label: 'Уведомления',
                onTap: () => _showComingSoon(context),
              ),
            ],
          ),
          const SizedBox(height: 20),
          _SettingsSection(
            title: 'Поддержка',
            items: [
              _SettingsTile(
                icon: Icons.help_outline_rounded,
                label: 'Помощь',
                onTap: () => _showComingSoon(context),
              ),
              _SettingsTile(
                icon: Icons.info_outline_rounded,
                label: 'О приложении',
                trailing: Text('v1.0.0', style: theme.textTheme.bodyMedium),
                onTap: () => _showAboutDialog(context),
              ),
            ],
          ),
          const SizedBox(height: 20),
          _SettingsSection(
            title: 'Аккаунт',
            items: [
              _SettingsTile(
                icon: Icons.logout_rounded,
                label: 'Выйти',
                labelColor: AppColors.error,
                iconColor: AppColors.error,
                trailing: const SizedBox.shrink(),
                onTap: () => context.read<AuthBloc>().add(const LogoutRequested()),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _showComingSoon(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Будет доступно в следующем обновлении')),
    );
  }

  void _showAboutDialog(BuildContext context) {
    showAboutDialog(
      context: context,
      applicationName: 'Ulya VPN',
      applicationVersion: '1.0.0',
      applicationLegalese: '© 2024 Ulya VPN',
    );
  }
}

class _ProfileCard extends StatelessWidget {
  const _ProfileCard({
    required this.name,
    required this.email,
    required this.balanceRubles,
  });

  final String name;
  final String? email;
  final double balanceRubles;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final initials = name
        .trim()
        .split(' ')
        .map((w) => w.isNotEmpty ? w[0] : '')
        .take(2)
        .join()
        .toUpperCase();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.divider),
      ),
      child: Row(
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
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                initials.isEmpty ? '?' : initials,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: theme.textTheme.titleMedium),
                if (email != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    email!,
                    style: theme.textTheme.bodyMedium,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.surfaceVariant,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.divider),
            ),
            child: Text(
              '${balanceRubles.toStringAsFixed(0)} ₽',
              style: theme.textTheme.labelLarge?.copyWith(
                color: AppColors.accent,
                fontSize: 12,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SettingsSection extends StatelessWidget {
  const _SettingsSection({required this.title, required this.items});

  final String title;
  final List<Widget> items;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            title,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: AppColors.textSecondary,
                  fontSize: 12,
                  letterSpacing: 0.8,
                ),
          ),
        ),
        Container(
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
        ),
      ],
    );
  }
}

class _SettingsTile extends StatelessWidget {
  const _SettingsTile({
    required this.icon,
    required this.label,
    this.trailing,
    this.onTap,
    this.labelColor,
    this.iconColor,
  });

  final IconData icon;
  final String label;
  final Widget? trailing;
  final VoidCallback? onTap;
  final Color? labelColor;
  final Color? iconColor;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: iconColor ?? AppColors.primary, size: 22),
      title: Text(
        label,
        style: Theme.of(context).textTheme.bodyLarge?.copyWith(
              color: labelColor,
            ),
      ),
      trailing: trailing ??
          const Icon(Icons.chevron_right_rounded,
              color: AppColors.textHint, size: 20),
      onTap: onTap,
    );
  }
}
