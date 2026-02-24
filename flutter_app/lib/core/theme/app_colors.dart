import 'package:flutter/material.dart';

/// Brand colours for Ulya VPN — premium dark theme.
class AppColors {
  AppColors._();

  // Backgrounds
  static const Color background = Color(0xFF0F172A);
  static const Color backgroundDark = Color(0xFF0B0F1A);

  // Gold accent
  static const Color accent = Color(0xFFF5C76B);
  static const Color accentDark = Color(0xFFE6B85C);

  // Glass surfaces
  static const Color glass = Color(0x14FFFFFF); // ~8% white
  static const Color glassLight = Color(0x26FFFFFF); // ~15% white
  static const Color glassBorder = Color(0x1AFFFFFF); // ~10% white border

  // Signal / success
  static const Color signal = Color(0xFF22C55E);

  // Text
  static const Color textPrimary = Color(0xFFE8E8F0);
  static const Color textSecondary = Color(0xFF8888AA);
  static const Color textHint = Color(0xFF555577);

  // Status
  static const Color success = Color(0xFF22C55E);
  static const Color error = Color(0xFFFF5C7A);
  static const Color warning = Color(0xFFFFB547);

  // Keep legacy names for auth screens compatibility
  static const Color primary = Color(0xFF6C63FF);
  static const Color primaryDark = Color(0xFF4B44CC);
  static const Color primaryLight = Color(0xFF9B94FF);
  static const Color surface = Color(0xFF1A1A2E);
  static const Color surfaceVariant = Color(0xFF222240);
  static const Color card = Color(0xFF1E1E35);
  static const Color divider = Color(0xFF2A2A45);
  static const Color inputBorder = Color(0xFF3A3A5C);
  static const Color inputFocusBorder = Color(0xFF6C63FF);
}
