import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';

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
                trailing: Text('v1.0.0',
                    style: theme.textTheme.bodyMedium),
                onTap: () => _showAboutDialog(context),
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
  });

  final IconData icon;
  final String label;
  final Widget? trailing;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: AppColors.primary, size: 22),
      title: Text(label, style: Theme.of(context).textTheme.bodyLarge),
      trailing: trailing ??
          const Icon(Icons.chevron_right_rounded,
              color: AppColors.textHint, size: 20),
      onTap: onTap,
    );
  }
}
