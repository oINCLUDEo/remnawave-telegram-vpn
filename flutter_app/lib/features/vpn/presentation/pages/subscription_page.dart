import 'dart:ui';
import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import '../widgets/glass_card.dart';
import '../widgets/tariff_card.dart';

class SubscriptionPage extends StatefulWidget {
  const SubscriptionPage({super.key});

  @override
  State<SubscriptionPage> createState() => _SubscriptionPageState();
}

class _SubscriptionPageState extends State<SubscriptionPage> {
  // 3 tariff cards (odd count) — 1 month / 3 months / 12 months
  static const _tariffs = [
    _Tariff('1 месяц', '299 ₽', '299 ₽/мес', null),
    _Tariff('3 месяца', '749 ₽', '250 ₽/мес', 16),
    _Tariff('12 месяцев', '1 999 ₽', '167 ₽/мес', 44),
  ];

  int _selectedTariff = 1; // default: 3 months

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: _buildAppBar(context),
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
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 20),
                _buildHeader(),
                const SizedBox(height: 24),
                _buildBenefits(),
                const SizedBox(height: 24),
                ...List.generate(_tariffs.length, (i) {
                  final t = _tariffs[i];
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: TariffCard(
                      duration: t.duration,
                      price: t.price,
                      pricePerMonth: t.pricePerMonth,
                      discountPercent: t.discount,
                      isSelected: _selectedTariff == i,
                      onTap: () => setState(() => _selectedTariff = i),
                    ),
                  );
                }),
                const SizedBox(height: 24),
                _buildContinueButton(),
                const SizedBox(height: 12),
                const Center(
                  child: Text(
                    'Отмена в любой момент. Без скрытых условий.',
                    style: TextStyle(
                        color: AppColors.textSecondary, fontSize: 12),
                    textAlign: TextAlign.center,
                  ),
                ),
                const SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar(BuildContext context) {
    return PreferredSize(
      preferredSize: const Size.fromHeight(56),
      child: ClipRect(
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            color: AppColors.background.withValues(alpha: 0.6),
            child: SafeArea(
              bottom: false,
              child: Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                child: Row(
                  children: [
                    if (Navigator.canPop(context))
                      IconButton(
                        icon: const Icon(Icons.arrow_back_ios_new_rounded,
                            color: AppColors.textPrimary, size: 20),
                        onPressed: () => Navigator.maybePop(context),
                      )
                    else
                      const SizedBox(width: 48),
                    const Expanded(
                      child: Text(
                        'Premium',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 17,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    const SizedBox(width: 48),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                    colors: [AppColors.accent, AppColors.accentDark]),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.workspace_premium_rounded,
                  color: Color(0xFF1A1200), size: 24),
            ),
            const SizedBox(width: 12),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Premium',
                  style: TextStyle(
                    color: AppColors.accent,
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  'Безлимитный доступ',
                  style: TextStyle(
                      color: AppColors.textSecondary, fontSize: 13),
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildBenefits() {
    const benefits = [
      (Icons.speed_rounded, 'Высокая скорость'),
      (Icons.all_inclusive_rounded, 'Безлимитный трафик'),
      (Icons.lock_rounded, 'Шифрование AES-256'),
      (Icons.devices_rounded, 'До 3 устройств'),
      (Icons.language_rounded, 'Доступ к Premium серверам'),
    ];

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: benefits.map((b) {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(
              children: [
                Icon(b.$1, color: AppColors.accent, size: 20),
                const SizedBox(width: 12),
                Text(
                  b.$2,
                  style: const TextStyle(
                      color: AppColors.textPrimary, fontSize: 14),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildContinueButton() {
    return GestureDetector(
      onTap: () {},
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [AppColors.accent, AppColors.accentDark],
          ),
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: AppColors.accent.withValues(alpha: 0.4),
              blurRadius: 20,
              spreadRadius: 0,
            ),
          ],
        ),
        child: const Text(
          'Продолжить',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Color(0xFF1A1200),
            fontSize: 16,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.5,
          ),
        ),
      ),
    );
  }
}

class _Tariff {
  const _Tariff(this.duration, this.price, this.pricePerMonth, this.discount);
  final String duration;
  final String price;
  final String pricePerMonth;
  final int? discount;
}
