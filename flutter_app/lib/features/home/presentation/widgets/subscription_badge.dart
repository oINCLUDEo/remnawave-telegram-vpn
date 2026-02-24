import 'dart:ui';

import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';

/// Subscription tier shown as an elegant glass pill badge.
enum SubscriptionTier { none, premium }

/// A compact glassmorphism badge that shows the user's subscription status.
///
/// Data must be provided by the caller; in a future sprint this will be driven
/// by a dedicated SubscriptionCubit that fetches data from the backend API.
class SubscriptionBadge extends StatelessWidget {
  const SubscriptionBadge({
    super.key,
    required this.tier,
    this.expiresAt,
  });

  final SubscriptionTier tier;

  /// Optional expiry date – shown when [tier] is [SubscriptionTier.premium].
  final DateTime? expiresAt;

  @override
  Widget build(BuildContext context) {
    final isPremium = tier == SubscriptionTier.premium;

    return ClipRRect(
      borderRadius: BorderRadius.circular(50),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: isPremium
                ? AppColors.primary.withValues(alpha: 0.18)
                : AppColors.glassBackground.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(50),
            border: Border.all(
              color: isPremium
                  ? AppColors.primary.withValues(alpha: 0.5)
                  : Colors.white.withValues(alpha: 0.12),
              width: 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                isPremium
                    ? Icons.workspace_premium_rounded
                    : Icons.info_outline_rounded,
                size: 14,
                color:
                    isPremium ? AppColors.primary : AppColors.textSecondary,
              ),
              const SizedBox(width: 6),
              Text(
                _label(isPremium),
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: isPremium ? AppColors.primary : AppColors.textSecondary,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _label(bool isPremium) {
    if (!isPremium) return 'Нет подписки';
    if (expiresAt == null) return 'Премиум';
    final d = expiresAt!;
    return 'Премиум · до ${d.day}.${d.month.toString().padLeft(2, '0')}.${d.year}';
  }
}
