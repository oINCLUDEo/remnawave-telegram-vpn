import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../domain/entities/renewal_option.dart';

/// A single renewal / purchase option tile.
class RenewalOptionTile extends StatelessWidget {
  const RenewalOptionTile({
    super.key,
    required this.option,
    required this.isSelected,
    required this.onTap,
  });

  final RenewalOption option;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final borderColor =
        isSelected ? AppColors.primary : AppColors.inputBorder;
    final bgColor =
        isSelected ? AppColors.primary.withValues(alpha: 0.12) : AppColors.card;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: borderColor, width: isSelected ? 2 : 1),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        child: Row(
          children: [
            // Period label
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    option.periodLabel,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (option.hasDiscount) ...[
                    const SizedBox(height: 2),
                    Text(
                      'Скидка ${option.discountPercent}%',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: AppColors.success,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            // Price
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '${option.priceRubles.toStringAsFixed(0)} ₽',
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: isSelected ? AppColors.primary : AppColors.textPrimary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                if (option.hasDiscount && option.originalPriceKopeks != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    '${(option.originalPriceKopeks! / 100).toStringAsFixed(0)} ₽',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontSize: 11,
                      decoration: TextDecoration.lineThrough,
                      color: AppColors.textHint,
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(width: 8),
            AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: 22,
              height: 22,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isSelected ? AppColors.primary : Colors.transparent,
                border: Border.all(
                  color: isSelected ? AppColors.primary : AppColors.inputBorder,
                  width: 2,
                ),
              ),
              child: isSelected
                  ? const Icon(Icons.check, size: 14, color: Colors.white)
                  : null,
            ),
          ],
        ),
      ),
    );
  }
}
