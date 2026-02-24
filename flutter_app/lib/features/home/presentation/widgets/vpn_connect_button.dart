import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/theme/app_colors.dart';
import '../cubit/vpn_cubit.dart';
import '../cubit/vpn_state.dart';

/// Large circular connect/disconnect button with neumorphism and glow effects.
///
/// Tapping the button calls [VpnCubit.toggleConnection].
/// The visual state (colors, shadow, glow) changes to reflect [VpnState].
///
/// Animation hooks are intentionally left as `TODO` comments so they can be
/// added in a future sprint without restructuring this widget.
class VpnConnectButton extends StatelessWidget {
  const VpnConnectButton({super.key});

  static const double _size = 148;

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<VpnCubit, VpnState>(
      builder: (context, state) {
        final isConnected = state is VpnConnected;
        final isTransitioning =
            state is VpnConnecting || state is VpnDisconnecting;

        // TODO(animation): wrap with AnimatedContainer / Lottie for transitions.
        return GestureDetector(
          onTap: isTransitioning
              ? null
              : () => context.read<VpnCubit>().toggleConnection(),
          child: _ButtonBody(
            isConnected: isConnected,
            isTransitioning: isTransitioning,
          ),
        );
      },
    );
  }
}

class _ButtonBody extends StatelessWidget {
  const _ButtonBody({
    required this.isConnected,
    required this.isTransitioning,
  });

  final bool isConnected;
  final bool isTransitioning;

  @override
  Widget build(BuildContext context) {
    final outerColor =
        isConnected ? AppColors.vpnActiveOuter : AppColors.vpnIdleOuter;
    final innerGradient = isConnected
        ? const LinearGradient(
            colors: [AppColors.vpnActiveGradientStart, AppColors.vpnActiveGradientEnd],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          )
        : const LinearGradient(
            colors: [AppColors.vpnIdleGradientStart, AppColors.vpnIdleGradientEnd],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          );
    final glowColor =
        isConnected ? AppColors.vpnActiveGlow : AppColors.vpnIdleGlow;
    final iconColor =
        isConnected ? AppColors.vpnActiveIcon : AppColors.vpnIdleIcon;

    return Container(
      width: VpnConnectButton._size + 24,
      height: VpnConnectButton._size + 24,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: outerColor,
        // Neumorphism: dual-tone shadow to create depth.
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.5),
            offset: const Offset(6, 6),
            blurRadius: 16,
          ),
          BoxShadow(
            color: Colors.white.withValues(alpha: 0.06),
            offset: const Offset(-4, -4),
            blurRadius: 12,
          ),
          // Glow ring.
          BoxShadow(
            color: glowColor.withValues(alpha: isConnected ? 0.45 : 0.22),
            blurRadius: isConnected ? 40 : 20,
            spreadRadius: isConnected ? 6 : 2,
          ),
        ],
      ),
      child: Center(
        child: Container(
          width: VpnConnectButton._size,
          height: VpnConnectButton._size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: innerGradient,
          ),
          child: Center(
            child: isTransitioning
                ? SizedBox(
                    width: 36,
                    height: 36,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                      color: iconColor,
                    ),
                  )
                : Icon(
                    isConnected
                        ? Icons.shield_rounded
                        : Icons.power_settings_new_rounded,
                    color: iconColor,
                    size: 52,
                  ),
          ),
        ),
      ),
    );
  }
}
