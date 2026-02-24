import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../widgets/glass_card.dart';

/// Placeholder for the Settings screen.
///
/// Wire up real settings in a future sprint.
class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Text('Настройки'),
        centerTitle: true,
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [AppColors.background, AppColors.backgroundDeep],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              const SizedBox(height: 8),
              GlassCard(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Column(
                  children: [
                    _SettingsTile(
                      icon: Icons.language_rounded,
                      label: 'Язык',
                      trailing: const Text(
                        'Русский',
                        style: TextStyle(
                            color: AppColors.textSecondary, fontSize: 13),
                      ),
                      onTap: () {},
                    ),
                    _divider(),
                    _SettingsTile(
                      icon: Icons.notifications_outlined,
                      label: 'Уведомления',
                      onTap: () {},
                    ),
                    _divider(),
                    _SettingsTile(
                      icon: Icons.info_outline_rounded,
                      label: 'О приложении',
                      trailing: const Text(
                        'v1.0.0',
                        style: TextStyle(
                            color: AppColors.textSecondary, fontSize: 13),
                      ),
                      onTap: () {},
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _divider() => const Divider(
        height: 1,
        color: AppColors.divider,
        indent: 16,
        endIndent: 16,
      );
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
      leading: Icon(icon, color: AppColors.primary, size: 20),
      title: Text(
        label,
        style: const TextStyle(
          color: AppColors.textPrimary,
          fontSize: 15,
          fontWeight: FontWeight.w500,
        ),
      ),
      trailing: trailing ??
          const Icon(Icons.chevron_right_rounded,
              color: AppColors.textSecondary, size: 20),
      onTap: onTap,
    );
  }
}
