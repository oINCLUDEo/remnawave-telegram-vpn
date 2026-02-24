import 'dart:ui';

import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';

class LocationsPage extends StatelessWidget {
  const LocationsPage({super.key});

  static const List<Map<String, String>> _servers = [
    {'flag': '🇳🇱', 'country': 'Netherlands', 'city': 'Amsterdam', 'ping': '12 мс'},
    {'flag': '🇩🇪', 'country': 'Germany', 'city': 'Frankfurt', 'ping': '18 мс'},
    {'flag': '🇫🇮', 'country': 'Finland', 'city': 'Helsinki', 'ping': '22 мс'},
    {'flag': '🇺🇸', 'country': 'United States', 'city': 'New York', 'ping': '85 мс'},
    {'flag': '🇬🇧', 'country': 'United Kingdom', 'city': 'London', 'ping': '30 мс'},
    {'flag': '🇯🇵', 'country': 'Japan', 'city': 'Tokyo', 'ping': '140 мс'},
    {'flag': '🇸🇬', 'country': 'Singapore', 'city': 'Singapore', 'ping': '110 мс'},
    {'flag': '🇨🇭', 'country': 'Switzerland', 'city': 'Zurich', 'ping': '25 мс'},
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0A14),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 16, 24, 8),
              child: Text(
                'Серверы',
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
                itemCount: _servers.length,
                separatorBuilder: (_, __) => const SizedBox(height: 10),
                itemBuilder: (context, index) {
                  final server = _servers[index];
                  return _ServerTile(server: server);
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ServerTile extends StatelessWidget {
  const _ServerTile({required this.server});
  final Map<String, String> server;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            color: const Color(0x1AFFFFFF),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0x33FFFFFF), width: 1),
          ),
          child: Row(
            children: [
              Text(server['flag']!, style: const TextStyle(fontSize: 26)),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      server['country']!,
                      style: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      server['city']!,
                      style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.success.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  server['ping']!,
                  style: TextStyle(
                    color: AppColors.success,
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Icon(Icons.chevron_right_rounded, color: AppColors.textSecondary, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}
