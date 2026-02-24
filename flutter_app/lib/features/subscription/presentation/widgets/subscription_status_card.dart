import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../domain/entities/subscription.dart';

/// Card showing the user's current subscription status.
class SubscriptionStatusCard extends StatelessWidget {
  const SubscriptionStatusCard({
    super.key,
    required this.subscription,
    this.onManage,
  });

  final Subscription subscription;
  final VoidCallback? onManage;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final statusColor = subscription.isActive
        ? AppColors.success
        : AppColors.error;
    final statusLabel = subscription.isExpired
        ? 'Истекла'
        : subscription.isActive
            ? 'Активна'
            : subscription.status;

    return Container(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF2A2A50), Color(0xFF1E1E3A)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.divider),
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  color: statusColor,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                statusLabel,
                style: theme.textTheme.labelLarge?.copyWith(
                  color: statusColor,
                ),
              ),
              const Spacer(),
              if (subscription.isTrial)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.warning.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: AppColors.warning.withValues(alpha: 0.4),
                    ),
                  ),
                  child: Text(
                    'Пробная',
                    style: theme.textTheme.labelLarge?.copyWith(
                      color: AppColors.warning,
                      fontSize: 11,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 16),
          if (subscription.tariffName != null) ...[
            Text(
              subscription.tariffName!,
              style: theme.textTheme.titleLarge,
            ),
            const SizedBox(height: 4),
          ],
          Text(
            subscription.isExpired
                ? 'Истёк ${_formatDate(subscription.endDate)}'
                : 'До ${_formatDate(subscription.endDate)}',
            style: theme.textTheme.bodyMedium,
          ),
          const SizedBox(height: 4),
          if (!subscription.isExpired)
            Text(
              subscription.timeLeftDisplay.isNotEmpty
                  ? 'Осталось: ${subscription.timeLeftDisplay}'
                  : 'Осталось: ${subscription.daysLeft} дн.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: subscription.daysLeft <= 3
                    ? AppColors.warning
                    : AppColors.textSecondary,
              ),
            ),
          const SizedBox(height: 16),
          _TrafficBar(subscription: subscription),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: onManage,
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(double.infinity, 44),
              ),
              child: const Text('Управление подпиской'),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.day.toString().padLeft(2, '0')}.'
        '${date.month.toString().padLeft(2, '0')}.'
        '${date.year}';
  }
}

class _TrafficBar extends StatelessWidget {
  const _TrafficBar({required this.subscription});

  final Subscription subscription;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isUnlimited = subscription.isUnlimited;
    final percent =
        (subscription.trafficUsedPercent / 100).clamp(0.0, 1.0);
    final barColor = percent > 0.9
        ? AppColors.error
        : percent > 0.7
            ? AppColors.warning
            : AppColors.accent;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Трафик',
              style: theme.textTheme.bodyMedium,
            ),
            Text(
              isUnlimited
                  ? '∞ безлимит'
                  : '${subscription.trafficUsedGb.toStringAsFixed(1)} / '
                      '${subscription.trafficLimitGb} ГБ',
              style: theme.textTheme.labelLarge?.copyWith(fontSize: 12),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (!isUnlimited) ...[
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: percent,
              backgroundColor: AppColors.divider,
              valueColor: AlwaysStoppedAnimation<Color>(barColor),
              minHeight: 6,
            ),
          ),
        ] else
          Container(
            height: 6,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppColors.accent, AppColors.primary],
              ),
              borderRadius: BorderRadius.circular(4),
            ),
          ),
      ],
    );
  }
}
