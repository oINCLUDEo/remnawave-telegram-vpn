import 'dart:ui';

import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with SingleTickerProviderStateMixin {
  bool _isConnected = false;
  bool _isConnecting = false;
  late AnimationController _glowController;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
    _glowAnimation = Tween<double>(begin: 0.6, end: 1.0).animate(
      CurvedAnimation(parent: _glowController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _glowController.dispose();
    super.dispose();
  }

  Future<void> _toggleConnection() async {
    if (_isConnecting) return;
    setState(() => _isConnecting = true);
    await Future<void>.delayed(const Duration(milliseconds: 1200));
    if (!mounted) return;
    setState(() {
      _isConnected = !_isConnected;
      _isConnecting = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0A14),
      body: SafeArea(
        child: Column(
          children: [
            _TopBar(),
            const SizedBox(height: 20),
            _SubscriptionBadge(),
            const Spacer(),
            _ConnectButton(
              isConnected: _isConnected,
              isConnecting: _isConnecting,
              glowAnimation: _glowAnimation,
              onTap: _toggleConnection,
            ),
            const SizedBox(height: 16),
            _StatusText(isConnected: _isConnected, isConnecting: _isConnecting),
            const Spacer(),
            _ServerCard(),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            'Ulya VPN',
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.5,
            ),
          ),
          Icon(Icons.shield_rounded, color: AppColors.primary, size: 28),
        ],
      ),
    );
  }
}

class _SubscriptionBadge extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Center(
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
            decoration: BoxDecoration(
              color: const Color(0x1AFFFFFF),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: const Color(0x33FFFFFF), width: 1),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.workspace_premium_rounded, color: AppColors.accent, size: 16),
                const SizedBox(width: 8),
                Text(
                  'Премиум активен до 1 мар 2026',
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ConnectButton extends StatelessWidget {
  const _ConnectButton({
    required this.isConnected,
    required this.isConnecting,
    required this.glowAnimation,
    required this.onTap,
  });

  final bool isConnected;
  final bool isConnecting;
  final Animation<double> glowAnimation;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final glowColor = isConnected ? AppColors.accent : AppColors.primary;

    return AnimatedBuilder(
      animation: glowAnimation,
      builder: (context, _) {
        return GestureDetector(
          onTap: onTap,
          child: Container(
            width: 220,
            height: 220,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: glowColor.withOpacity(0.15 * glowAnimation.value),
                  blurRadius: 60,
                  spreadRadius: 30,
                ),
                BoxShadow(
                  color: glowColor.withOpacity(0.25 * glowAnimation.value),
                  blurRadius: 30,
                  spreadRadius: 10,
                ),
              ],
            ),
            child: ClipOval(
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
                child: Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0x1AFFFFFF),
                    border: Border.all(
                      color: glowColor.withOpacity(0.5),
                      width: 2,
                    ),
                  ),
                  child: _ButtonContent(
                    isConnected: isConnected,
                    isConnecting: isConnecting,
                    glowColor: glowColor,
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _ButtonContent extends StatelessWidget {
  const _ButtonContent({
    required this.isConnected,
    required this.isConnecting,
    required this.glowColor,
  });

  final bool isConnected;
  final bool isConnecting;
  final Color glowColor;

  @override
  Widget build(BuildContext context) {
    if (isConnecting) {
      return Center(
        child: SizedBox(
          width: 48,
          height: 48,
          child: CircularProgressIndicator(
            strokeWidth: 3,
            valueColor: AlwaysStoppedAnimation<Color>(glowColor),
          ),
        ),
      );
    }
    return Center(
      child: Icon(
        isConnected ? Icons.check_circle_rounded : Icons.shield_rounded,
        size: 64,
        color: glowColor,
      ),
    );
  }
}

class _StatusText extends StatelessWidget {
  const _StatusText({required this.isConnected, required this.isConnecting});

  final bool isConnected;
  final bool isConnecting;

  @override
  Widget build(BuildContext context) {
    final String text;
    final Color color;
    if (isConnecting) {
      text = 'Подключение...';
      color = AppColors.warning;
    } else if (isConnected) {
      text = 'Защищено';
      color = AppColors.accent;
    } else {
      text = 'Отключен';
      color = AppColors.error;
    }

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      child: Text(
        text,
        key: ValueKey(text),
        style: TextStyle(
          color: color,
          fontSize: 18,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}

class _ServerCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: GestureDetector(
        onTap: () {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Выбор сервера скоро будет доступен'),
              behavior: SnackBarBehavior.floating,
            ),
          );
        },
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              decoration: BoxDecoration(
                color: const Color(0x1AFFFFFF),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0x33FFFFFF), width: 1),
              ),
              child: Row(
                children: [
                  const Text('🇳🇱', style: TextStyle(fontSize: 28)),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Netherlands',
                          style: TextStyle(
                            color: AppColors.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Рекомендуется',
                          style: TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.success.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: AppColors.success.withOpacity(0.3),
                        width: 1,
                      ),
                    ),
                    child: Text(
                      'Онлайн',
                      style: TextStyle(
                        color: AppColors.success,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Icon(Icons.chevron_right_rounded, color: AppColors.textSecondary),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
