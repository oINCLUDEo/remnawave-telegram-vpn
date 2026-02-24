import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import '../widgets/tariff_card.dart';

// ── Data models ──────────────────────────────────────────────────────────────

class _Benefit {
  const _Benefit({
    required this.icon,
    required this.title,
    required this.subtitle,
  });
  final IconData icon;
  final String title;
  final String subtitle;
}

const _benefits = [
  _Benefit(
    icon: Icons.format_list_bulleted_rounded,
    title: 'Белые списки',
    subtitle: 'Любимые сервисы в любой точке страны',
  ),
  _Benefit(
    icon: Icons.all_inclusive_rounded,
    title: 'Безлимитный трафик',
    subtitle: 'Без ограничений по скорости и объёму',
  ),
  _Benefit(
    icon: Icons.lock_rounded,
    title: 'Шифрование AES-256',
    subtitle: 'Максимальная защита ваших данных',
  ),
  _Benefit(
    icon: Icons.devices_rounded,
    title: 'До 3 устройств',
    subtitle: 'Подключайте несколько устройств одновременно',
  ),
  _Benefit(
    icon: Icons.language_rounded,
    title: 'Premium серверы',
    subtitle: 'Доступ к эксклюзивным быстрым серверам',
  ),
];

class _Tariff {
  const _Tariff(this.duration, this.price, this.pricePerMonth, this.discount);
  final String duration;
  final String price;
  final String pricePerMonth;
  final int? discount;
}

// ── Page ─────────────────────────────────────────────────────────────────────

class SubscriptionPage extends StatefulWidget {
  const SubscriptionPage({super.key});

  @override
  State<SubscriptionPage> createState() => _SubscriptionPageState();
}

class _SubscriptionPageState extends State<SubscriptionPage> {
  // 4 tariff options — 1 / 3 / 6 / 12 months
  static const _tariffs = [
    _Tariff('1 месяц', '299 ₽', '299 ₽/мес', null),
    _Tariff('3 месяца', '749 ₽', '250 ₽/мес', 16),
    _Tariff('6 месяцев', '1 299 ₽', '217 ₽/мес', 28),
    _Tariff('12 месяцев', '1 999 ₽', '167 ₽/мес', 44),
  ];

  int _selectedTariff = 1; // default: 3 months

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppColors.background, AppColors.backgroundDark],
          ),
        ),
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Page header ──
              _buildHeader(),
              const SizedBox(height: 12),

              // ── Benefits area — bounded by Expanded, never bleeds down ──
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Stack(
                    children: [
                      // Scrollable list fills the Expanded bounds exactly
                      _buildBenefitsList(),
                      // Gradient overlay at the bottom of the Expanded area gives
                      // the "scroll into shadow" effect without any container
                      // extending beyond this boundary.
                      Positioned(
                        left: 0,
                        right: 0,
                        // Extend 16px below the Expanded boundary so the gradient
                        // fully covers the container's bottom rounded corners.
                        bottom: -16,
                        child: IgnorePointer(
                          child: Container(
                            height: 100,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                                stops: const [0.0, 0.45, 1.0],
                                colors: [
                                  AppColors.background.withValues(alpha: 0),
                                  AppColors.background.withValues(alpha: 0.85),
                                  AppColors.background,
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              // ── Tariff box — sits directly on the gradient, no shared container ──
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 10, 20, 0),
                child: _buildTariffBox(),
              ),

              // ── Continue button — directly on gradient background ──
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 10, 20, 0),
                child: _buildContinueButton(),
              ),

              // ── Disclaimer — directly on gradient background ──
              const Padding(
                padding: EdgeInsets.fromLTRB(20, 8, 20, 8),
                child: Text(
                  'Отмена в любой момент. Без скрытых условий.',
                  style:
                      TextStyle(color: AppColors.textSecondary, fontSize: 11),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Row(
        children: [
          if (Navigator.canPop(context))
            GestureDetector(
              onTap: () => Navigator.maybePop(context),
              child: const Padding(
                padding: EdgeInsets.only(right: 12),
                child: Icon(Icons.arrow_back_ios_new_rounded,
                    color: AppColors.textPrimary, size: 20),
              ),
            ),
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                  colors: [AppColors.accent, AppColors.accentDark]),
              borderRadius: BorderRadius.circular(11),
            ),
            child: const Icon(Icons.workspace_premium_rounded,
                color: Color(0xFF1A1200), size: 22),
          ),
          const SizedBox(width: 12),
          const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Premium',
                style: TextStyle(
                  color: AppColors.accent,
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text(
                'Безлимитный доступ',
                style:
                    TextStyle(color: AppColors.textSecondary, fontSize: 12),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // Benefits list in the same style as the server list:
  // rounded container, items with icon + title + subtitle, thin dividers.
  // Positioned inside an Expanded — the container is strictly bounded.
  Widget _buildBenefitsList() {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF141B2D),
        borderRadius: BorderRadius.circular(16),
      ),
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(vertical: 4),
        itemCount: _benefits.length,
        separatorBuilder: (_, __) => const Divider(
          height: 1,
          thickness: 0.5,
          color: Color(0xFF1E2940),
          indent: 16,
          endIndent: 16,
        ),
        itemBuilder: (context, i) {
          final b = _benefits[i];
          return Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: AppColors.accent.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(b.icon, color: AppColors.accent, size: 18),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        b.title,
                        style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        b.subtitle,
                        style: const TextStyle(
                            color: AppColors.textSecondary, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  // Tariff cards grouped in their own rounded box — no other container wraps them.
  Widget _buildTariffBox() {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF141B2D),
        borderRadius: BorderRadius.circular(16),
      ),
      padding: const EdgeInsets.all(8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(_tariffs.length, (i) {
          final t = _tariffs[i];
          return Padding(
            padding:
                EdgeInsets.only(bottom: i < _tariffs.length - 1 ? 6 : 0),
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
      ),
    );
  }

  Widget _buildContinueButton() {
    return GestureDetector(
      onTap: () {},
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [AppColors.accent, AppColors.accentDark],
          ),
          borderRadius: BorderRadius.circular(14),
          boxShadow: [
            BoxShadow(
              color: AppColors.accent.withValues(alpha: 0.35),
              blurRadius: 16,
              spreadRadius: 0,
            ),
          ],
        ),
        child: const Text(
          'Продолжить',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Color(0xFF1A1200),
            fontSize: 15,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.5,
          ),
        ),
      ),
    );
  }
}
