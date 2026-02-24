import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import 'glass_card.dart';

/// Displays the currently selected VPN server in a glassmorphism card.
///
/// Tapping the card triggers [onTap] – typically navigating to the Locations
/// screen to let the user pick a different server.
///
/// In a future sprint the [location], [flagEmoji] and [isOnline] values will
/// come from a LocationsCubit fed by the backend API.
class ServerCard extends StatelessWidget {
  const ServerCard({
    super.key,
    required this.location,
    required this.flagEmoji,
    this.isOnline = true,
    this.isRecommended = false,
    this.onTap,
  });

  final String location;
  final String flagEmoji;
  final bool isOnline;
  final bool isRecommended;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: GlassCard(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        glowColor: AppColors.accent,
        borderOpacity: 0.18,
        child: Row(
          children: [
            // Flag / icon
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: AppColors.glassBackground.withValues(alpha: 0.25),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.1),
                ),
              ),
              child: Center(
                child: Text(
                  flagEmoji,
                  style: const TextStyle(fontSize: 22),
                ),
              ),
            ),
            const SizedBox(width: 14),

            // Location info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    location,
                    style: const TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Container(
                        width: 7,
                        height: 7,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: isOnline ? AppColors.success : AppColors.error,
                          boxShadow: [
                            BoxShadow(
                              color: (isOnline ? AppColors.success : AppColors.error)
                                  .withValues(alpha: 0.6),
                              blurRadius: 6,
                              spreadRadius: 1,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 5),
                      Text(
                        isRecommended ? 'Рекомендуется' : (isOnline ? 'Онлайн' : 'Офлайн'),
                        style: TextStyle(
                          color: isOnline ? AppColors.success : AppColors.textSecondary,
                          fontSize: 12,
                          fontWeight: FontWeight.w400,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Chevron
            Icon(
              Icons.chevron_right_rounded,
              color: AppColors.textSecondary.withValues(alpha: 0.7),
              size: 22,
            ),
          ],
        ),
      ),
    );
  }
}
