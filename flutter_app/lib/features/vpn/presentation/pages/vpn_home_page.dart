import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../../../../core/theme/app_colors.dart';
import '../widgets/glass_card.dart';
import '../widgets/neumorphic_button.dart';
import '../widgets/signal_indicator.dart';
import 'server_selection_page.dart';
import 'subscription_page.dart';

class VpnHomePage extends StatefulWidget {
  const VpnHomePage({super.key});

  @override
  State<VpnHomePage> createState() => _VpnHomePageState();
}

class _VpnHomePageState extends State<VpnHomePage> {
  bool _isConnected = false;
  String _selectedServer = 'Германия · Frankfurt';
  String _selectedServerFlag = '🇩🇪';
  double _trafficUsed = 0.34; // 34% used

  void _toggleConnection() {
    setState(() {
      _isConnected = !_isConnected;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: _buildAppBar(),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppColors.background, AppColors.backgroundDark],
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              children: [
                const SizedBox(height: 24),
                // Connect button
                Center(
                  child: NeumorphicButton(
                    isConnected: _isConnected,
                    onPressed: _toggleConnection,
                  ),
                ),
                const SizedBox(height: 24),
                // Status text
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 400),
                  child: Text(
                    _isConnected ? 'Защищено' : 'Не подключено',
                    key: ValueKey(_isConnected),
                    style: TextStyle(
                      color: _isConnected
                          ? AppColors.signal
                          : AppColors.textSecondary,
                      fontSize: 22,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
                if (_isConnected) ...[
                  const SizedBox(height: 4),
                  const Text(
                    'Ваше соединение зашифровано',
                    style: TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 13,
                    ),
                  ),
                ],
                const SizedBox(height: 28),
                // Traffic card
                GlassCard(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.data_usage_rounded,
                              color: AppColors.accent, size: 20),
                          const SizedBox(width: 8),
                          const Text(
                            'Трафик',
                            style: TextStyle(
                              color: AppColors.textSecondary,
                              fontSize: 13,
                            ),
                          ),
                          const Spacer(),
                          Text(
                            '${(100 - _trafficUsed * 100).toStringAsFixed(0)} ГБ осталось',
                            style: const TextStyle(
                              color: AppColors.textPrimary,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: LinearProgressIndicator(
                          value: _trafficUsed,
                          minHeight: 8,
                          backgroundColor: AppColors.glassBorder,
                          valueColor: const AlwaysStoppedAnimation<Color>(
                              AppColors.accent),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            '${(_trafficUsed * 100).toStringAsFixed(0)} ГБ использовано',
                            style: const TextStyle(
                                color: AppColors.textSecondary, fontSize: 11),
                          ),
                          const Text(
                            '100 ГБ',
                            style: TextStyle(
                                color: AppColors.textSecondary, fontSize: 11),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                // Server card
                GestureDetector(
                  onTap: () async {
                    final result = await Navigator.of(context).push<Map<String, String>>(
                      MaterialPageRoute(builder: (_) => const ServerSelectionPage()),
                    );
                    if (result != null) {
                      setState(() {
                        _selectedServer = result['name'] ?? _selectedServer;
                        _selectedServerFlag = result['flag'] ?? _selectedServerFlag;
                      });
                    }
                  },
                  child: GlassCard(
                    padding: const EdgeInsets.all(20),
                    child: Row(
                      children: [
                        Container(
                          width: 44,
                          height: 44,
                          decoration: BoxDecoration(
                            color: AppColors.glassLight,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Center(
                            child: Text(_selectedServerFlag,
                                style: const TextStyle(fontSize: 22)),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Текущий сервер',
                                style: TextStyle(
                                    color: AppColors.textSecondary,
                                    fontSize: 12),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                _selectedServer,
                                style: const TextStyle(
                                  color: AppColors.textPrimary,
                                  fontSize: 15,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                        SignalIndicator(
                          level: _isConnected ? 4 : 3,
                          color: _isConnected
                              ? AppColors.signal
                              : AppColors.textSecondary,
                        ),
                        const SizedBox(width: 8),
                        const Icon(Icons.chevron_right_rounded,
                            color: AppColors.textSecondary),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                // Premium card
                GestureDetector(
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const SubscriptionPage()),
                  ),
                  child: GlassCard(
                    padding: const EdgeInsets.all(20),
                    color: AppColors.accent.withValues(alpha: 0.08),
                    border: Border.all(
                        color: AppColors.accent.withValues(alpha: 0.3),
                        width: 1),
                    child: Row(
                      children: [
                        Container(
                          width: 44,
                          height: 44,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              colors: [AppColors.accent, AppColors.accentDark],
                            ),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(Icons.workspace_premium_rounded,
                              color: Color(0xFF1A1200), size: 22),
                        ),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Улучшить до Premium',
                                style: TextStyle(
                                  color: AppColors.accent,
                                  fontSize: 15,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              SizedBox(height: 2),
                              Text(
                                'Безлимитный трафик · Быстрые серверы',
                                style: TextStyle(
                                    color: AppColors.textSecondary,
                                    fontSize: 12),
                              ),
                            ],
                          ),
                        ),
                        const Icon(Icons.chevron_right_rounded,
                            color: AppColors.accent),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return PreferredSize(
      preferredSize: const Size.fromHeight(64),
      child: ClipRect(
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.background.withValues(alpha: 0.6),
              border: const Border(
                bottom: BorderSide(color: AppColors.glassBorder, width: 1),
              ),
            ),
            child: SafeArea(
              bottom: false,
              child: Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                child: Row(
                  children: [
                    // Logo
                    SvgPicture.asset(
                      'assets/images/logo.svg',
                      height: 28,
                      colorFilter: const ColorFilter.mode(
                          Colors.white, BlendMode.srcIn),
                    ),
                    const Spacer(),
                    // Signal indicator in appbar
                    SignalIndicator(
                      level: _isConnected ? 4 : 0,
                      color: _isConnected
                          ? AppColors.signal
                          : AppColors.textSecondary,
                    ),
                    const SizedBox(width: 16),
                    IconButton(
                      icon: const Icon(Icons.notifications_outlined,
                          color: AppColors.textSecondary, size: 22),
                      onPressed: () {},
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                    const SizedBox(width: 12),
                    IconButton(
                      icon: const Icon(Icons.settings_outlined,
                          color: AppColors.textSecondary, size: 22),
                      onPressed: () {},
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
