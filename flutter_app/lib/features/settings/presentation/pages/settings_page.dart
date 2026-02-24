import 'dart:ui';

import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0A14),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Настройки',
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 24),
              _GlassSection(
                children: [
                  _SettingsTile(
                    icon: Icons.language_outlined,
                    title: 'Язык',
                    subtitle: 'Русский',
                    onTap: () {},
                  ),
                  _Divider(),
                  _SettingsTile(
                    icon: Icons.dark_mode_outlined,
                    title: 'Тема',
                    subtitle: 'Тёмная',
                    onTap: () {},
                  ),
                  _Divider(),
                  _SettingsTile(
                    icon: Icons.notifications_outlined,
                    title: 'Уведомления',
                    subtitle: 'Включены',
                    onTap: () {},
                  ),
                ],
              ),
              const SizedBox(height: 16),
              _GlassSection(
                children: [
                  _SettingsTile(
                    icon: Icons.shield_outlined,
                    title: 'Протокол',
                    subtitle: 'Автоматически',
                    onTap: () {},
                  ),
                  _Divider(),
                  _SettingsTile(
                    icon: Icons.dns_outlined,
                    title: 'DNS',
                    subtitle: 'По умолчанию',
                    onTap: () {},
                  ),
                  _Divider(),
                  _SettingsTile(
                    icon: Icons.block_outlined,
                    title: 'Kill Switch',
                    subtitle: 'Выключен',
                    onTap: () {},
                  ),
                ],
              ),
              const SizedBox(height: 16),
              _GlassSection(
                children: [
                  _SettingsTile(
                    icon: Icons.help_outline_rounded,
                    title: 'Поддержка',
                    onTap: () {},
                  ),
                  _Divider(),
                  _SettingsTile(
                    icon: Icons.info_outline_rounded,
                    title: 'О приложении',
                    subtitle: 'v1.0.0',
                    onTap: () {},
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  const _SettingsTile({
    required this.icon,
    required this.title,
    this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String? subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 14),
        child: Row(
          children: [
            Icon(icon, color: AppColors.primary, size: 22),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                title,
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
            if (subtitle != null)
              Text(
                subtitle!,
                style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
              ),
            const SizedBox(width: 6),
            Icon(Icons.chevron_right_rounded, color: AppColors.textSecondary, size: 20),
          ],
        ),
      ),
    );
  }
}

class _Divider extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(height: 0.5, color: const Color(0x22FFFFFF));
  }
}

class _GlassSection extends StatelessWidget {
  const _GlassSection({required this.children});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          decoration: BoxDecoration(
            color: const Color(0x1AFFFFFF),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0x33FFFFFF), width: 1),
          ),
          child: Column(
            children: children,
          ),
        ),
      ),
    );
  }
}
