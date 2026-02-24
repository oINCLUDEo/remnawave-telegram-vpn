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
  double _trafficUsed = 0.34;

  void _toggleConnection() => setState(() => _isConnected = !_isConnected);

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
          child: LayoutBuilder(
            builder: (context, constraints) {
              final h = constraints.maxHeight;
              final w = constraints.maxWidth;
              // Button diameter: 50% of screen width, clamped for very small/large screens
              final btnDiameter = (w * 0.50).clamp(148.0, 195.0);
              // Vertical gaps proportional to available height
              final topGap = (h * 0.030).clamp(8.0, 24.0);
              final midGap = (h * 0.022).clamp(6.0, 16.0);

              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Column(
                  children: [
                    // Space above pushes all content toward the bottom navigation bar
                    const Spacer(),
                    Center(
                      child: NeumorphicButton(
                        isConnected: _isConnected,
                        onPressed: _toggleConnection,
                        diameter: btnDiameter,
                      ),
                    ),
                    SizedBox(height: midGap),
                    _buildStatusSection(),
                    SizedBox(height: midGap),
                    _buildTrafficCard(),
                    const SizedBox(height: 8),
                    _buildServerCard(context),
                    const SizedBox(height: 8),
                    _buildPremiumCard(context),
                    SizedBox(height: topGap),
                  ],
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  // Fixed-height status section prevents layout shifts on connect/disconnect.
  Widget _buildStatusSection() {
    return SizedBox(
      height: 36,
      child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 400),
        child: Column(
          key: ValueKey(_isConnected),
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              _isConnected ? 'Защищено' : 'Не подключено',
              style: TextStyle(
                color: _isConnected ? AppColors.signal : AppColors.textSecondary,
                fontSize: 20,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.5,
              ),
            ),
            if (_isConnected)
              const Text(
                'Ваше соединение зашифровано',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 11),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildTrafficCard() {
    return GlassCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.data_usage_rounded, color: AppColors.accent, size: 18),
              const SizedBox(width: 6),
              const Text('Трафик',
                  style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
              const Spacer(),
              Text(
                '${(100 - _trafficUsed * 100).toStringAsFixed(0)} ГБ осталось',
                style: const TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 12,
                    fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: _trafficUsed,
              minHeight: 6,
              backgroundColor: AppColors.glassBorder,
              valueColor: const AlwaysStoppedAnimation<Color>(AppColors.accent),
            ),
          ),
          const SizedBox(height: 6),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '${(_trafficUsed * 100).toStringAsFixed(0)} ГБ использовано',
                style: const TextStyle(color: AppColors.textSecondary, fontSize: 11),
              ),
              const Text('100 ГБ',
                  style: TextStyle(color: AppColors.textSecondary, fontSize: 11)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildServerCard(BuildContext context) {
    return GestureDetector(
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
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          children: [
            // Smaller flag box (36×36) to give more room to text
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: AppColors.glassLight,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Center(
                child: Text(_selectedServerFlag,
                    style: const TextStyle(fontSize: 18)),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Текущий сервер',
                      style: TextStyle(
                          color: AppColors.textSecondary, fontSize: 11)),
                  const SizedBox(height: 2),
                  Text(
                    _selectedServer,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            // Smaller signal indicator to avoid overlap with text
            SignalIndicator(
              level: _isConnected ? 4 : 3,
              height: 16,
              barWidth: 4,
              spacing: 2,
              color: _isConnected ? AppColors.signal : AppColors.textSecondary,
            ),
            const SizedBox(width: 6),
            const Icon(Icons.chevron_right_rounded,
                color: AppColors.textSecondary, size: 18),
          ],
        ),
      ),
    );
  }

  Widget _buildPremiumCard(BuildContext context) {
    return GestureDetector(
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => const SubscriptionPage()),
      ),
      child: GlassCard(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        color: AppColors.accent.withValues(alpha: 0.08),
        border:
            Border.all(color: AppColors.accent.withValues(alpha: 0.3), width: 1),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                    colors: [AppColors.accent, AppColors.accentDark]),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.workspace_premium_rounded,
                  color: Color(0xFF1A1200), size: 20),
            ),
            const SizedBox(width: 10),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Улучшить до Premium',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: AppColors.accent,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  SizedBox(height: 2),
                  Text(
                    'Безлимитный трафик · Быстрые серверы',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style:
                        TextStyle(color: AppColors.textSecondary, fontSize: 11),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded,
                color: AppColors.accent, size: 18),
          ],
        ),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return PreferredSize(
      // Extra top padding gives the header more breathing room from the status bar
      preferredSize: const Size.fromHeight(56),
      child: Container(
        // Transparent — blends seamlessly with the body gradient, no visual separator
        color: Colors.transparent,
        child: SafeArea(
          bottom: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
            child: Row(
              children: [
                SvgPicture.asset(
                  'assets/images/logo.svg',
                  height: 26,
                  colorFilter:
                      const ColorFilter.mode(Colors.white, BlendMode.srcIn),
                ),
                const Spacer(),
                SignalIndicator(
                  level: _isConnected ? 4 : 0,
                  color: _isConnected ? AppColors.signal : AppColors.textSecondary,
                ),
                const SizedBox(width: 14),
                IconButton(
                  icon: const Icon(Icons.notifications_outlined,
                      color: AppColors.textSecondary, size: 20),
                  onPressed: () {},
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
                const SizedBox(width: 10),
                IconButton(
                  icon: const Icon(Icons.settings_outlined,
                      color: AppColors.textSecondary, size: 20),
                  onPressed: () {},
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
