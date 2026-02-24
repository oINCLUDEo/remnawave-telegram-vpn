import 'package:flutter/material.dart';

/// Brand colours for Ulya VPN.
class AppColors {
  AppColors._();

  // Primary palette
  static const Color primary = Color(0xFF6C63FF);
  static const Color primaryDark = Color(0xFF4B44CC);
  static const Color primaryLight = Color(0xFF9B94FF);

  // Accent
  static const Color accent = Color(0xFF00D4AA);

  // Backgrounds
  static const Color background = Color(0xFF0F0F1A);
  static const Color surface = Color(0xFF1A1A2E);
  static const Color surfaceVariant = Color(0xFF222240);
  static const Color card = Color(0xFF1E1E35);

  // Text
  static const Color textPrimary = Color(0xFFE8E8F0);
  static const Color textSecondary = Color(0xFF8888AA);
  static const Color textHint = Color(0xFF555577);

  // Status
  static const Color success = Color(0xFF00C896);
  static const Color error = Color(0xFFFF5C7A);
  static const Color warning = Color(0xFFFFB547);

  // Misc
  static const Color divider = Color(0xFF2A2A45);
  static const Color inputBorder = Color(0xFF3A3A5C);
  static const Color inputFocusBorder = Color(0xFF6C63FF);

  // Glass / blur overlays
  static const Color glassWhite = Color(0x0DFFFFFF);   // 5 % white
  static const Color glassBorder = Color(0x1AFFFFFF);  // 10 % white border
  static const Color glassDark = Color(0xB31A1A2E);    // 70 % surface for nav bar
}
