import 'package:flutter/material.dart';

/// Paints a subtle dot-grid pattern over any background.
/// Dots are very small and low-opacity so they don't overpower the gradient.
class DotGridBackground extends StatelessWidget {
  const DotGridBackground({
    super.key,
    required this.child,
    this.dotColor = const Color(0x22FFFFFF),
    this.dotRadius = 1.0,
    this.spacing = 22.0,
  });

  final Widget child;
  final Color dotColor;
  final double dotRadius;
  final double spacing;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _DotGridPainter(
        dotColor: dotColor,
        dotRadius: dotRadius,
        spacing: spacing,
      ),
      child: child,
    );
  }
}

class _DotGridPainter extends CustomPainter {
  const _DotGridPainter({
    required this.dotColor,
    required this.dotRadius,
    required this.spacing,
  });

  final Color dotColor;
  final double dotRadius;
  final double spacing;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = dotColor
      ..style = PaintingStyle.fill;

    for (double x = spacing / 2; x < size.width; x += spacing) {
      for (double y = spacing / 2; y < size.height; y += spacing) {
        canvas.drawCircle(Offset(x, y), dotRadius, paint);
      }
    }
  }

  @override
  bool shouldRepaint(_DotGridPainter old) =>
      old.dotColor != dotColor ||
      old.dotRadius != dotRadius ||
      old.spacing != spacing;
}
