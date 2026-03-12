import 'package:flutter/material.dart';

import '../models/me_response.dart';
import '../services/auth_state.dart';
import '../services/me_service.dart';
import '../services/subscription_api_service.dart';
import '../theme/app_colors.dart';
import '../widgets/purple_header.dart';
import 'auth_bottom_sheet.dart';

// ─────────────────────────────────────────────────────────────────────────────
// PremiumPage — subscription builder / upgrade screen
// ─────────────────────────────────────────────────────────────────────────────

class PremiumPage extends StatefulWidget {
  const PremiumPage({super.key});

  @override
  State<PremiumPage> createState() => _PremiumPageState();
}

class _PremiumPageState extends State<PremiumPage>
    with SingleTickerProviderStateMixin {
  // ── Builder state ─────────────────────────────────────────────────────────
  int _days = 30;
  int _trafficGb = 30;
  int _devices = 1;

  // ── Price ─────────────────────────────────────────────────────────────────
  CalcResult? _price;
  double? _displayedPriceRub; // animated display value
  bool _calcLoading = false;
  bool _buyLoading = false;
  String? _errorMessage;

  // ── Upgrade diff state ────────────────────────────────────────────────────
  String? _upgradeAction;

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
      _displayedPriceRub = result?.priceRub;
      _calcLoading = false;
    });
  }

  // ── Purchase ──────────────────────────────────────────────────────────────

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
        setState(() =>
            _errorMessage = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _buyLoading = false);
    }
  }

  // ── Upgrade ───────────────────────────────────────────────────────────────

  Future<void> _onUpgrade(String action, int value) async {
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
      final url = await SubscriptionApiService.upgradeSubscription(
        action: action,
        value: value,
      );
      if (!mounted) return;

      if (url == 'balance') {
        _showSnack('Улучшение применено с баланса!');
        await MeService.refresh();
      } else if (url != null) {
        await SubscriptionApiService.openPaymentUrl(url);
        _showSnack('Перейдите по ссылке для оплаты');
      } else {
        setState(() => _errorMessage = 'Не удалось создать платёж');
      }
    } on Exception catch (e) {
      if (mounted) {
        setState(() =>
            _errorMessage = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _buyLoading = false);
    }
  }

  void _showSnack(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), duration: const Duration(seconds: 3)),
    );
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final auth = authStateNotifier.value;
    final me = meNotifier.value;
    final hasSub = me?.subscription?.isActive ?? false;

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
                title: hasSub ? 'Улучшить' : 'Premium',
                subtitle: hasSub
                    ? 'Расширьте возможности подписки'
                    : 'Настройте и купите подписку',
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 100),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                const SizedBox(height: 8),

                // ── Auth prompt ────────────────────────────────────────────
                if (!auth.isLoggedIn) ...[
                  _AuthPromptCard(onLogin: () => showAuthBottomSheet(context)),
                  const SizedBox(height: 12),
                ],

                // ── Upgrade diff view (if has subscription) ────────────────
                if (hasSub && me?.subscription != null) ...[
                  _UpgradeDiffCard(
                    sub: me!.subscription!,
                    selectedAction: _upgradeAction,
                    onActionSelected: (action) =>
                        setState(() => _upgradeAction = action),
                    loading: _buyLoading,
                    onConfirm: _upgradeAction == null
                        ? null
                        : () => _onUpgrade(
                              _upgradeAction!,
                              _upgradeAction == 'traffic'
                                  ? 15
                                  : _upgradeAction == 'devices'
                                      ? 1
                                      : 30,
                            ),
                  ),
                  const SizedBox(height: 12),
                ],

                // ── Subscription builder (always shown) ────────────────────
                _BuilderCard(
                  days: _days,
                  trafficGb: _trafficGb,
                  devices: _devices,
                  dayOptions: _dayOptions,
                  trafficOptions: _trafficOptions,
                  maxDevices: _maxDevices,
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

                // ── Animated price preview ─────────────────────────────────
                _PriceCard(
                  price: _price,
                  displayedPriceRub: _displayedPriceRub,
                  calcLoading: _calcLoading,
                  buyLoading: _buyLoading,
                  errorMessage: _errorMessage,
                  isLoggedIn: auth.isLoggedIn,
                  balanceRub: me?.balanceRub ?? 0.0,
                  onBuyYookassa: () => _onBuy(method: 'yookassa'),
                  onBuyBalance: () => _onBuy(method: 'balance'),
                ),
                const SizedBox(height: 16),

                // ── Benefits ───────────────────────────────────────────────
                _BenefitsCard(),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// _AuthPromptCard
// ─────────────────────────────────────────────────────────────────────────────

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
            child:
                const Icon(Icons.telegram, color: Color(0xFF229ED9), size: 20),
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
                const Text(
                  'Авторизация через Telegram',
                  style: TextStyle(
                      color: AppColors.textNeutralMuted, fontSize: 12),
                ),
              ],
            ),
          ),
          FilledButton(
            onPressed: onLogin,
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFF229ED9),
              padding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
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

// ─────────────────────────────────────────────────────────────────────────────
// _UpgradeDiffCard — current plan vs upgrade comparison
// ─────────────────────────────────────────────────────────────────────────────

class _UpgradeDiffCard extends StatelessWidget {
  final MeSubscription sub;
  final String? selectedAction;
  final ValueChanged<String?> onActionSelected;
  final bool loading;
  final VoidCallback? onConfirm;

  const _UpgradeDiffCard({
    required this.sub,
    required this.selectedAction,
    required this.onActionSelected,
    required this.loading,
    required this.onConfirm,
  });

  @override
  Widget build(BuildContext context) {
    final trafficLabel = sub.trafficLimitGb == 0
        ? '∞ безлимит'
        : '${sub.trafficLimitGb} ГБ';

    final options = [
      _UpgradeOption(
        action: 'traffic',
        icon: Icons.data_usage,
        iconColor: const Color(0xFF00D9FF),
        label: 'Трафик',
        currentValue: trafficLabel,
        newValue: sub.trafficLimitGb == 0
            ? '∞ безлимит'
            : '+15 ГБ → ${sub.trafficLimitGb + 15} ГБ',
      ),
      _UpgradeOption(
        action: 'devices',
        icon: Icons.devices,
        iconColor: AppColors.primary,
        label: 'Устройства',
        currentValue: '${sub.deviceLimit} уст.',
        newValue: '+1 → ${sub.deviceLimit + 1} уст.',
      ),
      _UpgradeOption(
        action: 'days',
        icon: Icons.calendar_today_outlined,
        iconColor: AppColors.success,
        label: 'Срок',
        currentValue: sub.formattedExpiry,
        newValue: '+30 дней',
      ),
    ];

    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Улучшить подписку',
            style: TextStyle(
              color: AppColors.textNeutralMain,
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Выберите параметр для улучшения',
            style: TextStyle(
                color: AppColors.textNeutralMuted, fontSize: 12),
          ),
          const SizedBox(height: 14),

          // Option rows
          ...options.map((opt) {
            final isSelected = selectedAction == opt.action;
            return GestureDetector(
              onTap: () =>
                  onActionSelected(isSelected ? null : opt.action),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 150),
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: isSelected
                      ? opt.iconColor.withValues(alpha: 0.1)
                      : AppColors.graphiteElevated,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isSelected
                        ? opt.iconColor.withValues(alpha: 0.5)
                        : Colors.white.withValues(alpha: 0.06),
                    width: isSelected ? 1.5 : 1,
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        color: opt.iconColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Icon(opt.icon,
                          color: opt.iconColor, size: 18),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            opt.label,
                            style: const TextStyle(
                              color: AppColors.textNeutralMain,
                              fontWeight: FontWeight.w600,
                              fontSize: 13,
                            ),
                          ),
                          const SizedBox(height: 2),
                          // Diff row
                          Row(
                            children: [
                              Text(
                                opt.currentValue,
                                style: const TextStyle(
                                  color: AppColors.textNeutralMuted,
                                  fontSize: 11,
                                ),
                              ),
                              const Padding(
                                padding:
                                    EdgeInsets.symmetric(horizontal: 4),
                                child: Icon(
                                  Icons.arrow_forward,
                                  color: AppColors.textNeutralMuted,
                                  size: 10,
                                ),
                              ),
                              Text(
                                opt.newValue,
                                style: TextStyle(
                                  color: isSelected
                                      ? opt.iconColor
                                      : AppColors.textNeutralSecondary,
                                  fontSize: 11,
                                  fontWeight: isSelected
                                      ? FontWeight.bold
                                      : FontWeight.normal,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    if (isSelected)
                      Icon(Icons.check_circle,
                          color: opt.iconColor, size: 18)
                    else
                      const Icon(Icons.radio_button_unchecked,
                          color: AppColors.textNeutralMuted, size: 18),
                  ],
                ),
              ),
            );
          }),

          if (selectedAction != null) ...[
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: loading ? null : onConfirm,
                icon: loading
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.upgrade, size: 18),
                label: const Text(
                  'Улучшить и оплатить',
                  style: TextStyle(
                      fontSize: 14, fontWeight: FontWeight.w600),
                ),
                style: FilledButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _UpgradeOption {
  final String action;
  final IconData icon;
  final Color iconColor;
  final String label;
  final String currentValue;
  final String newValue;

  const _UpgradeOption({
    required this.action,
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.currentValue,
    required this.newValue,
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// _BuilderCard — Apple-style subscription configurator
// ─────────────────────────────────────────────────────────────────────────────

class _BuilderCard extends StatelessWidget {
  final int days;
  final int trafficGb;
  final int devices;
  final List<int> dayOptions;
  final List<int> trafficOptions;
  final int maxDevices;
  final ValueChanged<int> onDaysChanged;
  final ValueChanged<int> onTrafficChanged;
  final ValueChanged<int> onDevicesChanged;

  const _BuilderCard({
    required this.days,
    required this.trafficGb,
    required this.devices,
    required this.dayOptions,
    required this.trafficOptions,
    required this.maxDevices,
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
            'Конфигуратор',
            style: TextStyle(
              color: AppColors.textNeutralMain,
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
          const SizedBox(height: 16),

          // Duration
          _SectionLabel('Длительность'),
          const SizedBox(height: 8),
          Row(
            children: dayOptions.map((d) {
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
          _SectionLabel('Трафик'),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: trafficOptions.map((gb) {
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
          _SectionLabel('Устройства'),
          const SizedBox(height: 8),
          Row(
            children: [
              _CircleButton(
                icon: Icons.remove,
                enabled: devices > 1,
                onTap: () => onDevicesChanged(devices - 1),
              ),
              const SizedBox(width: 14),
              Text(
                '$devices',
                style: const TextStyle(
                  color: AppColors.textNeutralMain,
                  fontWeight: FontWeight.bold,
                  fontSize: 26,
                ),
              ),
              const SizedBox(width: 14),
              _CircleButton(
                icon: Icons.add,
                enabled: devices < maxDevices,
                onTap: () => onDevicesChanged(devices + 1),
              ),
              const SizedBox(width: 12),
              Text(
                devices == 1 ? 'устройство' : 'устройств',
                style: const TextStyle(
                    color: AppColors.textNeutralSecondary, fontSize: 13),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// _PriceCard — animated price + purchase buttons
// ─────────────────────────────────────────────────────────────────────────────

class _PriceCard extends StatefulWidget {
  final CalcResult? price;
  final double? displayedPriceRub;
  final bool calcLoading;
  final bool buyLoading;
  final String? errorMessage;
  final bool isLoggedIn;
  final double balanceRub;
  final VoidCallback onBuyYookassa;
  final VoidCallback onBuyBalance;

  const _PriceCard({
    required this.price,
    required this.displayedPriceRub,
    required this.calcLoading,
    required this.buyLoading,
    required this.errorMessage,
    required this.isLoggedIn,
    required this.balanceRub,
    required this.onBuyYookassa,
    required this.onBuyBalance,
  });

  @override
  State<_PriceCard> createState() => _PriceCardState();
}

class _PriceCardState extends State<_PriceCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _scale;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    _scale = Tween<double>(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeOut),
    );
  }

  @override
  void didUpdateWidget(_PriceCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.displayedPriceRub != widget.displayedPriceRub &&
        widget.displayedPriceRub != null) {
      _ctrl.forward().then((_) => _ctrl.reverse());
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

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
              if (widget.calcLoading)
                const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: AppColors.primary),
                )
              else
                ScaleTransition(
                  scale: _scale,
                  child: Text(
                    widget.displayedPriceRub != null
                        ? '${widget.displayedPriceRub!.toStringAsFixed(0)} ₽'
                        : '—',
                    style: const TextStyle(
                      color: AppColors.primary,
                      fontWeight: FontWeight.bold,
                      fontSize: 28,
                    ),
                  ),
                ),
            ],
          ),

          if (widget.errorMessage != null) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: AppColors.danger.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                widget.errorMessage!,
                style: const TextStyle(
                    color: AppColors.danger, fontSize: 12),
              ),
            ),
          ],

          const SizedBox(height: 16),

          // YooKassa button
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: (widget.price == null ||
                      widget.calcLoading ||
                      widget.buyLoading)
                  ? null
                  : widget.onBuyYookassa,
              icon: widget.buyLoading
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.payment, size: 18),
              label: const Text(
                'Оплатить картой / СБП',
                style: TextStyle(
                    fontSize: 15, fontWeight: FontWeight.w600),
              ),
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ),

          // Balance button (only when logged in)
          if (widget.isLoggedIn) ...[
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: (widget.price == null ||
                        widget.calcLoading ||
                        widget.buyLoading)
                    ? null
                    : widget.onBuyBalance,
                icon: const Icon(
                    Icons.account_balance_wallet_outlined,
                    size: 18),
                label: Text(
                  'Списать с баланса (${widget.balanceRub.toStringAsFixed(0)} ₽)',
                  style: const TextStyle(
                      fontSize: 14, fontWeight: FontWeight.w600),
                ),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.textNeutralMain,
                  side: BorderSide(
                      color: Colors.white.withValues(alpha: 0.15)),
                  padding:
                      const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// _BenefitsCard
// ─────────────────────────────────────────────────────────────────────────────

class _BenefitsCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    const benefits = [
      (Icons.speed, Color(0xFF00D9FF), 'Высокая скорость',
          'Без ограничений для стриминга и игр'),
      (Icons.public, Color(0xFF2ED573), 'Серверы по всему миру',
          'Более 20 стран на выбор'),
      (Icons.lock_outline, Colors.amber, 'Без логов',
          'Полная конфиденциальность'),
      (Icons.support_agent, Color(0xFFFFA502), 'Поддержка',
          'Ответ за 1 час через Telegram'),
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

// ─────────────────────────────────────────────────────────────────────────────
// Shared small widgets
// ─────────────────────────────────────────────────────────────────────────────

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

class _SectionLabel extends StatelessWidget {
  final String text;

  const _SectionLabel(this.text);

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
        padding: const EdgeInsets.symmetric(vertical: 10),
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
              color:
                  selected ? AppColors.primary : AppColors.textNeutralSecondary,
              fontWeight:
                  selected ? FontWeight.bold : FontWeight.normal,
              fontSize: 13,
            ),
          ),
        ),
      ),
    );
  }
}

class _CircleButton extends StatelessWidget {
  final IconData icon;
  final bool enabled;
  final VoidCallback onTap;

  const _CircleButton({
    required this.icon,
    required this.enabled,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: enabled ? onTap : null,
      child: Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          color: enabled
              ? AppColors.primary.withValues(alpha: 0.15)
              : AppColors.graphiteElevated,
          shape: BoxShape.circle,
          border: Border.all(
            color: enabled
                ? AppColors.primary.withValues(alpha: 0.4)
                : Colors.white.withValues(alpha: 0.06),
          ),
        ),
        child: Icon(
          icon,
          size: 18,
          color: enabled
              ? AppColors.primary
              : AppColors.textNeutralMuted,
        ),
      ),
    );
  }
}
