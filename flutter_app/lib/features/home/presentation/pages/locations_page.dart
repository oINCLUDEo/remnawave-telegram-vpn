import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../widgets/glass_card.dart';

/// Placeholder for the Locations / Server List screen.
///
/// Replace with a real server list widget in a future sprint.
class LocationsPage extends StatelessWidget {
  const LocationsPage({super.key});

  // TODO(servers): populate from LocationsCubit / backend API.
  static const _servers = [
    _Server('🇳🇱', 'Нидерланды, Амстердам', true, true),
    _Server('🇩🇪', 'Германия, Франкфурт', true, false),
    _Server('🇺🇸', 'США, Нью-Йорк', true, false),
    _Server('🇸🇬', 'Сингапур', true, false),
    _Server('🇬🇧', 'Великобритания, Лондон', true, false),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Text('Серверы'),
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
          child: ListView.separated(
            padding: const EdgeInsets.all(20),
            itemCount: _servers.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final s = _servers[index];
              return GlassCard(
                padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                child: Row(
                  children: [
                    Text(s.flag, style: const TextStyle(fontSize: 22)),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Text(
                        s.name,
                        style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 15,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                    if (s.recommended)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: AppColors.accent.withValues(alpha: 0.18),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: AppColors.accent.withValues(alpha: 0.5),
                          ),
                        ),
                        child: const Text(
                          'Рекомендуется',
                          style: TextStyle(
                            color: AppColors.accent,
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      )
                    else
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: s.online ? AppColors.success : AppColors.error,
                        ),
                      ),
                  ],
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _Server {
  const _Server(this.flag, this.name, this.online, this.recommended);
  final String flag;
  final String name;
  final bool online;
  final bool recommended;
}
