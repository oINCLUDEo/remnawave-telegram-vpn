import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';

/// A connect button with neumorphic styling and press/glow animations.
class NeumorphicButton extends StatefulWidget {
  const NeumorphicButton({
    super.key,
    required this.onPressed,
    required this.isConnected,
    this.diameter = 240.0,
  });

  final VoidCallback onPressed;
  final bool isConnected;
  final double diameter;

  @override
  State<NeumorphicButton> createState() => _NeumorphicButtonState();
}

class _NeumorphicButtonState extends State<NeumorphicButton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _scaleAnim;
  late final Animation<double> _glowAnim;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 150),
    );
    _scaleAnim = Tween<double>(begin: 1.0, end: 0.93).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
    _glowAnim = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Color get _glowColor =>
      widget.isConnected ? AppColors.signal : AppColors.accent;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => _controller.forward(),
      onTapUp: (_) {
        _controller.reverse();
        widget.onPressed();
      },
      onTapCancel: () => _controller.reverse(),
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          return Transform.scale(
            scale: _scaleAnim.value,
            child: Container(
              width: widget.diameter,
              height: widget.diameter,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    widget.isConnected
                        ? const Color(0xFF1A3A2A)
                        : const Color(0xFF1A1F35),
                    const Color(0xFF0F172A),
                  ],
                ),
                boxShadow: [
                  // Outer glow
                  BoxShadow(
                    color: _glowColor.withValues(
                        alpha: 0.35 + _glowAnim.value * 0.2),
                    blurRadius: 40 + _glowAnim.value * 20,
                    spreadRadius: 2 + _glowAnim.value * 4,
                  ),
                  // Neumorphic dark shadow
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.6),
                    blurRadius: 20,
                    offset: const Offset(8, 8),
                  ),
                  // Neumorphic light highlight
                  BoxShadow(
                    color: Colors.white.withValues(alpha: 0.04),
                    blurRadius: 20,
                    offset: const Offset(-8, -8),
                  ),
                ],
                border: Border.all(
                  color: _glowColor.withValues(alpha: 0.3),
                  width: 1.5,
                ),
              ),
              child: child,
            ),
          );
        },
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              child: Icon(
                widget.isConnected ? Icons.shield_rounded : Icons.shield_outlined,
                key: ValueKey(widget.isConnected),
                size: 64,
                color: widget.isConnected ? AppColors.signal : AppColors.accent,
              ),
            ),
            const SizedBox(height: 8),
            // Fixed-height container prevents the column from re-centering
            // when text switches between 1 line ("ПОДКЛЮЧЕНО") and 2 lines
            // ("НАЖМИТЕ\nДЛЯ ВХОДА"), which caused the icon to jump vertically.
            SizedBox(
              height: 28,
              child: Text(
                widget.isConnected ? 'ПОДКЛЮЧЕНО' : 'НАЖМИТЕ\nДЛЯ ВХОДА',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: widget.isConnected
                      ? AppColors.signal
                      : AppColors.textSecondary,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.5,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
