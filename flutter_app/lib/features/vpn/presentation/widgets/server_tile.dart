import 'dart:ui';
import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import 'signal_indicator.dart';
import 'premium_badge.dart';

class ServerTile extends StatefulWidget {
  const ServerTile({
    super.key,
    required this.name,
    required this.countryCode,
    required this.flagEmoji,
    this.isPremium = false,
    required this.signalLevel,
    required this.isSelected,
    required this.onTap,
  });

  final String name;
  final String countryCode;
  final String flagEmoji;
  final bool isPremium;
  final int signalLevel;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  State<ServerTile> createState() => _ServerTileState();
}

class _ServerTileState extends State<ServerTile>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _scaleAnim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 120),
      lowerBound: 0.97,
      upperBound: 1.0,
    )..value = 1.0;
    _scaleAnim = _ctrl;
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => _ctrl.reverse(),
      onTapUp: (_) {
        _ctrl.forward();
        widget.onTap();
      },
      onTapCancel: () => _ctrl.forward(),
      child: ScaleTransition(
        scale: _scaleAnim,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              decoration: BoxDecoration(
                color: widget.isSelected
                    ? AppColors.accent.withValues(alpha: 0.1)
                    : AppColors.glass,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: widget.isSelected
                      ? AppColors.accent.withValues(alpha: 0.6)
                      : AppColors.glassBorder,
                  width: 1,
                ),
              ),
              child: Row(
                children: [
                  // Flag / icon
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: AppColors.glassLight,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Center(
                      child: Text(widget.flagEmoji, style: const TextStyle(fontSize: 22)),
                    ),
                  ),
                  const SizedBox(width: 12),
                  // Name + badge
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              widget.name,
                              style: const TextStyle(
                                color: AppColors.textPrimary,
                                fontSize: 15,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            if (widget.isPremium) ...[
                              const SizedBox(width: 6),
                              const PremiumBadge(),
                            ],
                          ],
                        ),
                        const SizedBox(height: 2),
                        Text(
                          widget.countryCode,
                          style: const TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                  SignalIndicator(level: widget.signalLevel),
                  if (widget.isSelected) ...[
                    const SizedBox(width: 8),
                    const Icon(Icons.check_circle_rounded,
                        color: AppColors.accent, size: 18),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
