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

class _SubscriptionPageState extends State<SubscriptionPage>
    with SingleTickerProviderStateMixin {
  int _planIndex = 0;
  int _selectedTariff = 2;
  late final TabController _tabController;

  final _premiumTariffs = const [
    _Tariff('1 месяц', '299 ₽', '299 ₽/мес', null),
    _Tariff('3 месяца', '749 ₽', '250 ₽/мес', 16),
    _Tariff('6 месяцев', '1 299 ₽', '217 ₽/мес', 28),
    _Tariff('12 месяцев', '1 999 ₽', '167 ₽/мес', 44),
  ];

  final _ultraTariffs = const [
    _Tariff('1 месяц', '499 ₽', '499 ₽/мес', null),
    _Tariff('3 месяца', '1 299 ₽', '433 ₽/мес', 13),
    _Tariff('6 месяцев', '2 299 ₽', '383 ₽/мес', 23),
    _Tariff('12 месяцев', '3 999 ₽', '333 ₽/мес', 33),
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(() {
      if (!_tabController.indexIsChanging) return;
      setState(() {
        _planIndex = _tabController.index;
        _selectedTariff = 2;
      });
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  List<_Tariff> get _currentTariffs =>
      _planIndex == 0 ? _premiumTariffs : _ultraTariffs;

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
                const SizedBox(height: 16),
                _buildSegmentedControl(),
                const SizedBox(height: 28),
                _buildBenefits(),
                const SizedBox(height: 24),
                ...List.generate(_currentTariffs.length, (i) {
                  final t = _currentTariffs[i];
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
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.arrow_back_ios_new_rounded,
                          color: AppColors.textPrimary, size: 20),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                    const Expanded(
                      child: Text(
                        'Подписка',
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

  Widget _buildSegmentedControl() {
    return GlassCard(
      padding: const EdgeInsets.all(4),
      borderRadius: BorderRadius.circular(14),
      child: Row(
        children: ['Premium', 'Ultra'].asMap().entries.map((e) {
          final selected = _planIndex == e.key;
          return Expanded(
            child: GestureDetector(
              onTap: () {
                _tabController.animateTo(e.key);
                setState(() {
                  _planIndex = e.key;
                  _selectedTariff = 2;
                });
              },
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                padding: const EdgeInsets.symmetric(vertical: 10),
                decoration: BoxDecoration(
                  gradient: selected
                      ? const LinearGradient(
                          colors: [AppColors.accent, AppColors.accentDark])
                      : null,
                  borderRadius: BorderRadius.circular(10),
                  boxShadow: selected
                      ? [
                          BoxShadow(
                            color: AppColors.accent.withValues(alpha: 0.3),
                            blurRadius: 8,
                          )
                        ]
                      : null,
                ),
                child: Text(
                  e.value,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: selected
                        ? const Color(0xFF1A1200)
                        : AppColors.textSecondary,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildBenefits() {
    final benefits = _planIndex == 0
        ? [
            (Icons.speed_rounded, 'Высокая скорость'),
            (Icons.all_inclusive_rounded, 'Безлимитный трафик'),
            (Icons.lock_rounded, 'Шифрование AES-256'),
            (Icons.devices_rounded, 'До 3 устройств'),
          ]
        : [
            (Icons.rocket_launch_rounded, 'Максимальная скорость'),
            (Icons.all_inclusive_rounded, 'Безлимитный трафик'),
            (Icons.security_rounded, 'Шифрование AES-256-GCM'),
            (Icons.devices_rounded, 'До 5 устройств'),
            (Icons.star_rounded, 'Эксклюзивные серверы'),
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
