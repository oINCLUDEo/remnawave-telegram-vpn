import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../widgets/glass_card.dart';
import '../widgets/subscription_badge.dart';

/// Placeholder for the Subscription / Premium screen.
///
/// Shows subscription details and plan benefits in a premium glass style.
/// Replace with real data from a SubscriptionCubit in a future sprint.
class SubscriptionPage extends StatelessWidget {
  const SubscriptionPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Text('Подписка'),
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
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 8),

                // Current status badge
                const Center(
                  child: SubscriptionBadge(
                    // TODO(subscription): replace with real tier from API.
                    tier: SubscriptionTier.none,
                  ),
                ),
                const SizedBox(height: 32),

                // Premium plan card
                GlassCard(
                  glowColor: AppColors.primary,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(
                            Icons.workspace_premium_rounded,
                            color: AppColors.primary,
                            size: 22,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            'Премиум план',
                            style:
                                Theme.of(context).textTheme.titleMedium?.copyWith(
                                      color: AppColors.primary,
                                    ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),
                      ..._benefits.map(
                        (b) => Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Row(
                            children: [
                              const Icon(
                                Icons.check_circle_outline_rounded,
                                color: AppColors.accent,
                                size: 18,
                              ),
                              const SizedBox(width: 10),
                              Text(
                                b,
                                style: const TextStyle(
                                  color: AppColors.textPrimary,
                                  fontSize: 14,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 32),

                // TODO(payment): replace with real payment flow.
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () {},
                    child: const Text('Получить Премиум'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  static const _benefits = [
    'YouTube и стриминг без рекламы',
    'Белые и чёрные списки сайтов',
    'Высокая скорость без ограничений',
    'Несколько устройств одновременно',
    'Приоритетная поддержка',
  ];
}
