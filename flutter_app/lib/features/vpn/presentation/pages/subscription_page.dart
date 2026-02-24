import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/di/injection.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../subscription/domain/entities/tariff_period.dart';
import '../../../subscription/domain/entities/tariff_plan.dart';
import '../../../subscription/presentation/cubit/tariff_cubit.dart';
import '../../../subscription/presentation/cubit/tariff_state.dart';
import '../widgets/tariff_card.dart';

// ── Static benefit rows (displayed regardless of API state) ──────────────────

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

// ── Fallback static tariff data (shown when not logged in / API unavailable) ─

class _StaticPeriod {
  const _StaticPeriod(this.label, this.priceLabel, this.pricePerMonthLabel,
      this.discountPercent);
  final String label;
  final String priceLabel;
  final String pricePerMonthLabel;
  final int? discountPercent;
}

const _staticPeriods = [
  _StaticPeriod('1 месяц', '299 ₽', '299 ₽/мес', null),
  _StaticPeriod('3 месяца', '749 ₽', '250 ₽/мес', 16),
  _StaticPeriod('6 месяцев', '1 299 ₽', '217 ₽/мес', 28),
  _StaticPeriod('12 месяцев', '1 999 ₽', '167 ₽/мес', 44),
];

// ── Page ─────────────────────────────────────────────────────────────────────

/// Wraps [_SubscriptionView] with a [TariffCubit] from the DI container.
class SubscriptionPage extends StatelessWidget {
  const SubscriptionPage({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<TariffCubit>(
      create: (_) => sl<TariffCubit>()..loadTariffs(),
      child: const _SubscriptionView(),
    );
  }
}

class _SubscriptionView extends StatefulWidget {
  const _SubscriptionView();

  @override
  State<_SubscriptionView> createState() => _SubscriptionViewState();
}

class _SubscriptionViewState extends State<_SubscriptionView> {
  /// Fallback selected index used when API is unavailable.
  int _staticSelectedIndex = 1;

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
          child: BlocBuilder<TariffCubit, TariffState>(
            builder: (context, state) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildHeader(),
                  const SizedBox(height: 12),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      child: Stack(
                        children: [
                          _buildBenefitsList(),
                          Positioned(
                            left: 0,
                            right: 0,
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
                                      AppColors.background
                                          .withValues(alpha: 0),
                                      AppColors.background
                                          .withValues(alpha: 0.85),
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
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 10, 20, 0),
                    child: _buildTariffBox(state),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 10, 20, 0),
                    child: _buildContinueButton(),
                  ),
                  const Padding(
                    padding: EdgeInsets.fromLTRB(20, 8, 20, 8),
                    child: Text(
                      'Отмена в любой момент. Без скрытых условий.',
                      style: TextStyle(
                          color: AppColors.textSecondary, fontSize: 11),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
              );
            },
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

  Widget _buildBenefitsList() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Container(
        color: const Color(0xFF141B2D),
        child: ListView.builder(
          padding: EdgeInsets.zero,
          itemCount: _benefits.length,
          itemBuilder: (context, i) {
            final b = _benefits[i];
            final rowColor = i.isEven
                ? const Color(0xFF141B2D)
                : const Color(0xFF1A2236);
            return ColoredBox(
              color: rowColor,
              child: Padding(
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
                      child:
                          Icon(b.icon, color: AppColors.accent, size: 18),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(b.title,
                              style: const TextStyle(
                                color: AppColors.textPrimary,
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                              )),
                          const SizedBox(height: 2),
                          Text(b.subtitle,
                              style: const TextStyle(
                                  color: AppColors.textSecondary,
                                  fontSize: 12)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildTariffBox(TariffState state) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF141B2D),
        borderRadius: BorderRadius.circular(16),
      ),
      padding: const EdgeInsets.all(8),
      child: switch (state) {
        TariffLoading() => const Padding(
            padding: EdgeInsets.symmetric(vertical: 24),
            child: Center(
              child: SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: AppColors.accent,
                ),
              ),
            ),
          ),
        TariffLoaded() => _buildApiPeriods(state),
        TariffError() => _buildErrorWithRetry(),
        _ => _buildStaticPeriods(),
      },
    );
  }

  /// Periods fetched from the API for the selected tariff plan.
  Widget _buildApiPeriods(TariffLoaded state) {
    final TariffPlan plan = state.selectedPlan;
    final List<TariffPeriod> periods = plan.periods;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(periods.length, (i) {
        final p = periods[i];
        return Padding(
          padding: EdgeInsets.only(bottom: i < periods.length - 1 ? 6 : 0),
          child: TariffCard(
            duration: p.label,
            price: p.priceLabel,
            pricePerMonth: p.pricePerMonthLabel,
            discountPercent: p.discountPercent,
            isSelected: state.selectedPeriodIndex == i,
            onTap: () =>
                context.read<TariffCubit>().selectPeriod(i),
          ),
        );
      }),
    );
  }

  /// Static periods shown when API is unavailable or user not authenticated.
  Widget _buildStaticPeriods() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(_staticPeriods.length, (i) {
        final t = _staticPeriods[i];
        return Padding(
          padding: EdgeInsets.only(
              bottom: i < _staticPeriods.length - 1 ? 6 : 0),
          child: TariffCard(
            duration: t.label,
            price: t.priceLabel,
            pricePerMonth: t.pricePerMonthLabel,
            discountPercent: t.discountPercent,
            isSelected: _staticSelectedIndex == i,
            onTap: () => setState(() => _staticSelectedIndex = i),
          ),
        );
      }),
    );
  }

  /// Shown when API returned a non-auth error.
  Widget _buildErrorWithRetry() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'Не удалось загрузить тарифы',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          GestureDetector(
            onTap: () => context.read<TariffCubit>().loadTariffs(),
            child: Text(
              'Повторить',
              style: TextStyle(
                color: AppColors.accent.withValues(alpha: 0.9),
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
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
