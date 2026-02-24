import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';

/// Displays a cellular-signal-style indicator with N bars.
class SignalIndicator extends StatelessWidget {
  const SignalIndicator({
    super.key,
    this.level = 4,
    this.maxLevel = 5,
    this.color = AppColors.signal,
    this.height = 20.0,
    this.spacing = 3.0,
    this.barWidth = 5.0,
  });

  final int level;
  final int maxLevel;
  final Color color;
  final double height;
  final double spacing;
  final double barWidth;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      mainAxisSize: MainAxisSize.min,
      children: List.generate(maxLevel, (i) {
        final barHeight = height * (0.3 + 0.7 * (i + 1) / maxLevel);
        final isActive = i < level;
        return Padding(
          padding: EdgeInsets.only(left: i == 0 ? 0 : spacing),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            width: barWidth,
            height: barHeight,
            decoration: BoxDecoration(
              color: isActive
                  ? color
                  : color.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        );
      }),
    );
  }
}
