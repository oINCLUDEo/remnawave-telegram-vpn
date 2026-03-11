import 'package:flutter/material.dart';

import '../models/me_response.dart';
import '../services/me_service.dart';
import '../services/subscription_api_service.dart';
import '../theme/app_colors.dart';
import '../widgets/purple_header.dart';
import 'auth_bottom_sheet.dart';
import '../services/auth_state.dart';

class PremiumPage extends StatefulWidget {
  const PremiumPage({super.key});

  @override
  State<PremiumPage> createState() => _PremiumPageState();
}

class _PremiumPageState extends State<PremiumPage> {
  // ── Builder state ─────────────────────────────────────────────────────────
  int _days = 30;
  int _trafficGb = 30;  // 0 = unlimited
  int _devices = 1;

  // ── Price ─────────────────────────────────────────────────────────────────
  CalcResult? _price;
  bool _calcLoading = false;
  bool _buyLoading = false;
  String? _errorMessage;

  static const _dayOptions = [30, 60, 90];
  static const _trafficOptions = [15, 30, 50, 0]; // 0 = unlimited
  static const _maxDevices = 5;

  @override
  void initState() {
    super.initState();
    meNotifier.addListener(_onMeChanged);
    authStateNotifier.addListener(_onAuthChanged);
    _recalculate();
  }

  @override
  void dispose() {
    meNotifier.removeListener(_onMeChanged);
    authStateNotifier.removeListener(_onAuthChanged);
    super.dispose();
  }

  void _onMeChanged() {
    if (mounted) setState(() {});
  }

  void _onAuthChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _recalculate() async {
    if (!mounted) return;
    setState(() {
      _calcLoading = true;
      _errorMessage = null;
    });
    final result = await SubscriptionApiService.calcPrice(
      days: _days,
      trafficGb: _trafficGb,
      devices: _devices,
    );
    if (!mounted) return;
    setState(() {
      _price = result;
      _calcLoading = false;
    });
  }

  Future<void> _onBuy({String method = 'yookassa'}) async {
    final auth = authStateNotifier.value;
    if (!auth.isLoggedIn) {
      await showAuthBottomSheet(context);
      return;
    }

    setState(() {
      _buyLoading = true;
      _errorMessage = null;
    });

    try {
      final url = await SubscriptionApiService.buySubscription(
        days: _days,
        trafficGb: _trafficGb,
        devices: _devices,
        paymentMethod: method,
      );

      if (!mounted) return;

      if (url == 'balance') {
        _showSnack('Подписка успешно оплачена с баланса!');
        await MeService.refresh();
      } else if (url != null) {
        await SubscriptionApiService.openPaymentUrl(url);
        _showSnack('Перейдите по ссылке для оплаты');
      } else {
        setState(() => _errorMessage = 'Не удалось создать платёж');
      }
    } on Exception catch (e) {
      if (mounted) {
        setState(() => _errorMessage = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _buyLoading = false);
    }
  }

  void _showSnack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), duration: const Duration(seconds: 3)),
    );
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final auth = authStateNotifier.value;
    final me = meNotifier.value;
    final hasActiveSub = me?.subscription?.isActive ?? false;

    return Scaffold(
      backgroundColor: AppColors.graphiteBackground,
      body: CustomScrollView(
        slivers: [
          SliverPadding(
            padding: EdgeInsets.fromLTRB(
              16,
              MediaQuery.of(context).padding.top + 16,
              16,
              8,
            ),
            sliver: SliverToBoxAdapter(
              child: PurpleHeader(
                title: hasActiveSub ? 'Улучшить' : 'Premium',
                subtitle: hasActiveSub
                    ? 'Расширьте возможности подписки'
                    : 'Конфигуратор подписки',
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 100),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                const SizedBox(height: 8),

                // Auth prompt if not logged in
                if (!auth.isLoggedIn) ...[
                  _AuthPromptCard(onLogin: () => showAuthBottomSheet(context)),
                  const SizedBox(height: 12),
                ],

                // Subscription builder
                _BuilderCard(
                  days: _days,
                  trafficGb: _trafficGb,
                  devices: _devices,
                  onDaysChanged: (v) {
                    setState(() => _days = v);
                    _recalculate();
                  },
                  onTrafficChanged: (v) {
                    setState(() => _trafficGb = v);
                    _recalculate();
                  },
                  onDevicesChanged: (v) {
                    setState(() => _devices = v);
                    _recalculate();
                  },
                ),
                const SizedBox(height: 12),

                // Price preview
                _PriceCard(
                  price: _price,
                  loading: _calcLoading,
                  buyLoading: _buyLoading,
                  errorMessage: _errorMessage,
                  isLoggedIn: auth.isLoggedIn,
                  balanceRub: me?.balanceRub ?? 0.0,
                  onBuyYookassa: () => _onBuy(method: 'yookassa'),
                  onBuyBalance: () => _onBuy(method: 'balance'),
                ),
                const SizedBox(height: 16),

                // Benefits (collapsed)
                _BenefitsCard(),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Auth prompt ───────────────────────────────────────────────────────────────

class _AuthPromptCard extends StatelessWidget {
  final VoidCallback onLogin;

  const _AuthPromptCard({required this.onLogin});

  @override
  Widget build(BuildContext context) {
    return _Card(
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: const Color(0xFF229ED9).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.telegram, color: Color(0xFF229ED9), size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Войдите для покупки',
                  style: TextStyle(
                    color: AppColors.textNeutralMain,
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Авторизация через Telegram',
                  style: TextStyle(color: AppColors.textNeutralMuted, fontSize: 12),
                ),
              ],
            ),
          ),
          FilledButton(
            onPressed: onLogin,
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFF229ED9),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            child: const Text('Войти', style: TextStyle(fontSize: 13)),
          ),
        ],
      ),
    );
  }
}

// ── Builder card ──────────────────────────────────────────────────────────────

class _BuilderCard extends StatelessWidget {
  final int days;
  final int trafficGb;
  final int devices;
  final ValueChanged<int> onDaysChanged;
  final ValueChanged<int> onTrafficChanged;
  final ValueChanged<int> onDevicesChanged;

  static const _dayOptions = [30, 60, 90];
  static const _trafficOptions = [15, 30, 50, 0];
  static const _maxDevices = 5;

  const _BuilderCard({
    required this.days,
    required this.trafficGb,
    required this.devices,
    required this.onDaysChanged,
    required this.onTrafficChanged,
    required this.onDevicesChanged,
  });

  @override
  Widget build(BuildContext context) {
    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Конфигуратор подписки',
            style: TextStyle(
              color: AppColors.textNeutralMain,
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
          const SizedBox(height: 16),

          // Duration
          _Label('Длительность'),
          const SizedBox(height: 6),
          Row(
            children: _dayOptions.map((d) {
              final selected = days == d;
              return Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: _OptionChip(
                    label: '$d дн.',
                    selected: selected,
                    onTap: () => onDaysChanged(d),
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 14),

          // Traffic
          _Label('Трафик'),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: _trafficOptions.map((gb) {
              final selected = trafficGb == gb;
              final label = gb == 0 ? '∞ безлимит' : '$gb ГБ';
              return _OptionChip(
                label: label,
                selected: selected,
                onTap: () => onTrafficChanged(gb),
              );
            }).toList(),
          ),
          const SizedBox(height: 14),

          // Devices
          _Label('Устройства'),
          const SizedBox(height: 6),
          Row(
            children: [
              IconButton(
                icon: const Icon(Icons.remove_circle_outline, color: AppColors.textNeutralSecondary),
                onPressed: devices > 1 ? () => onDevicesChanged(devices - 1) : null,
                visualDensity: VisualDensity.compact,
              ),
              const SizedBox(width: 4),
              Text(
                '$devices',
                style: const TextStyle(
                  color: AppColors.textNeutralMain,
                  fontWeight: FontWeight.bold,
                  fontSize: 20,
                ),
              ),
              const SizedBox(width: 4),
              IconButton(
                icon: const Icon(Icons.add_circle_outline, color: AppColors.textNeutralSecondary),
                onPressed: devices < _maxDevices ? () => onDevicesChanged(devices + 1) : null,
                visualDensity: VisualDensity.compact,
              ),
              const SizedBox(width: 8),
              Text(
                'устройств одновременно',
                style: const TextStyle(color: AppColors.textNeutralSecondary, fontSize: 12),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Price card ────────────────────────────────────────────────────────────────

class _PriceCard extends StatelessWidget {
  final CalcResult? price;
  final bool loading;
  final bool buyLoading;
  final String? errorMessage;
  final bool isLoggedIn;
  final double balanceRub;
  final VoidCallback onBuyYookassa;
  final VoidCallback onBuyBalance;

  const _PriceCard({
    required this.price,
    required this.loading,
    required this.buyLoading,
    required this.errorMessage,
    required this.isLoggedIn,
    required this.balanceRub,
    required this.onBuyYookassa,
    required this.onBuyBalance,
  });

  @override
  Widget build(BuildContext context) {
    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Стоимость',
                style: TextStyle(
                  color: AppColors.textNeutralMain,
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
              if (loading)
                const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: AppColors.primary,
                  ),
                )
              else
                Text(
                  price != null ? '${price!.priceRub.toStringAsFixed(0)} ₽' : '—',
                  style: const TextStyle(
                    color: AppColors.primary,
                    fontWeight: FontWeight.bold,
                    fontSize: 24,
                  ),
                ),
            ],
          ),

          if (errorMessage != null) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: AppColors.danger.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                errorMessage!,
                style: const TextStyle(color: AppColors.danger, fontSize: 12),
              ),
            ),
          ],

          const SizedBox(height: 16),

          // Pay via YooKassa
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: (price == null || loading || buyLoading) ? null : onBuyYookassa,
              icon: buyLoading
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.payment, size: 18),
              label: const Text(
                'Оплатить картой / СБП',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
              ),
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ),

          // Pay from balance (only if logged in)
          if (isLoggedIn) ...[
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: (price == null || loading || buyLoading) ? null : onBuyBalance,
                icon: const Icon(Icons.account_balance_wallet_outlined, size: 18),
                label: Text(
                  'Списать с баланса (${balanceRub.toStringAsFixed(0)} ₽)',
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                ),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.textNeutralMain,
                  side: BorderSide(color: Colors.white.withValues(alpha: 0.15)),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

// ── Benefits card ─────────────────────────────────────────────────────────────

class _BenefitsCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    const benefits = [
      (Icons.speed, Color(0xFF00D9FF), 'Высокая скорость', 'Без ограничений для стриминга и игр'),
      (Icons.public, Color(0xFF2ED573), 'Серверы по всему миру', 'Более 20 стран на выбор'),
      (Icons.lock_outline, Colors.amber, 'Без логов', 'Полная конфиденциальность'),
      (Icons.support_agent, Color(0xFFFFA502), 'Поддержка', 'Ответ за 1 час через Telegram'),
    ];

    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Что включено',
            style: TextStyle(
              color: AppColors.textNeutralMain,
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
          const SizedBox(height: 12),
          ...benefits.map(
            (b) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                children: [
                  Icon(b.$1, color: b.$2, size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          b.$3,
                          style: const TextStyle(
                            color: AppColors.textNeutralMain,
                            fontWeight: FontWeight.w500,
                            fontSize: 13,
                          ),
                        ),
                        Text(
                          b.$4,
                          style: const TextStyle(
                            color: AppColors.textNeutralMuted,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Shared ────────────────────────────────────────────────────────────────────

class _Card extends StatelessWidget {
  final Widget child;

  const _Card({required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.graphiteSurface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
      ),
      child: child,
    );
  }
}

class _Label extends StatelessWidget {
  final String text;

  const _Label(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: AppColors.textNeutralSecondary,
        fontSize: 12,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.3,
      ),
    );
  }
}

class _OptionChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _OptionChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: selected
              ? AppColors.primary.withValues(alpha: 0.2)
              : AppColors.graphiteElevated,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: selected
                ? AppColors.primary.withValues(alpha: 0.6)
                : Colors.white.withValues(alpha: 0.06),
            width: selected ? 1.5 : 1,
          ),
        ),
        child: Center(
          child: Text(
            label,
            style: TextStyle(
              color: selected ? AppColors.primary : AppColors.textNeutralSecondary,
              fontWeight: selected ? FontWeight.bold : FontWeight.normal,
              fontSize: 13,
            ),
          ),
        ),
      ),
    );
  }
}
