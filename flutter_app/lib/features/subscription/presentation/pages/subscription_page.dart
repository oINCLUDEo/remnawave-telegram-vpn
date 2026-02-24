import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/theme/app_colors.dart';
import '../bloc/subscription_bloc.dart';
import '../bloc/subscription_event.dart';
import '../bloc/subscription_state.dart';
import '../widgets/renewal_option_tile.dart';
import '../widgets/subscription_status_card.dart';

/// Full subscription management screen.
class SubscriptionPage extends StatefulWidget {
  const SubscriptionPage({super.key});

  @override
  State<SubscriptionPage> createState() => _SubscriptionPageState();
}

class _SubscriptionPageState extends State<SubscriptionPage> {
  int? _selectedOptionIndex;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Подписка'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () {
              context
                  .read<SubscriptionBloc>()
                  .add(const SubscriptionRefreshRequested());
              setState(() => _selectedOptionIndex = null);
            },
          ),
        ],
      ),
      body: BlocBuilder<SubscriptionBloc, SubscriptionState>(
        builder: (context, state) {
          if (state is SubscriptionLoading || state is SubscriptionInitial) {
            return const Center(
              child: CircularProgressIndicator(color: AppColors.primary),
            );
          }
          if (state is SubscriptionError) {
            return _ErrorView(
              message: state.message,
              onRetry: () => context
                  .read<SubscriptionBloc>()
                  .add(const SubscriptionLoadRequested()),
            );
          }
          if (state is SubscriptionLoaded) {
            return RefreshIndicator(
              color: AppColors.primary,
              onRefresh: () async {
                context
                    .read<SubscriptionBloc>()
                    .add(const SubscriptionRefreshRequested());
                setState(() => _selectedOptionIndex = null);
              },
              child: _buildContent(context, state),
            );
          }
          return const SizedBox.shrink();
        },
      ),
    );
  }

  Widget _buildContent(BuildContext context, SubscriptionLoaded state) {
    final theme = Theme.of(context);
    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Current subscription card
          if (state.subscription != null) ...[
            SubscriptionStatusCard(subscription: state.subscription!),
            const SizedBox(height: 28),
          ] else ...[
            _NoSubscriptionBanner(),
            const SizedBox(height: 28),
          ],

          // Renewal / purchase options
          if (state.renewalOptions.isNotEmpty) ...[
            Text(
              state.subscription != null
                  ? 'Продлить подписку'
                  : 'Выбрать план',
              style: theme.textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            ...List.generate(state.renewalOptions.length, (i) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: RenewalOptionTile(
                  option: state.renewalOptions[i],
                  isSelected: _selectedOptionIndex == i,
                  onTap: () => setState(() => _selectedOptionIndex = i),
                ),
              );
            }),
            const SizedBox(height: 16),
            if (_selectedOptionIndex != null)
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => _showPaymentDialog(context, state),
                  child: Text(
                    'Оплатить '
                    '${state.renewalOptions[_selectedOptionIndex!].priceRubles.toStringAsFixed(0)} ₽',
                  ),
                ),
              ),
          ],
        ],
      ),
    );
  }

  void _showPaymentDialog(BuildContext context, SubscriptionLoaded state) {
    final option = state.renewalOptions[_selectedOptionIndex!];
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        title: const Text('Подтверждение'),
        content: Text(
          'Оплата подписки «${option.periodLabel}» на сумму '
          '${option.priceRubles.toStringAsFixed(0)} ₽\n\n'
          'Функция оплаты будет доступна в следующем обновлении.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Закрыть'),
          ),
        ],
      ),
    );
  }
}

class _NoSubscriptionBanner extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        children: [
          const Icon(
            Icons.shield_outlined,
            size: 56,
            color: AppColors.textHint,
          ),
          const SizedBox(height: 16),
          Text(
            'Нет активной подписки',
            style: theme.textTheme.titleLarge,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            'Выберите план ниже, чтобы получить доступ ко всем серверам.',
            style: theme.textTheme.bodyMedium,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.error_outline_rounded,
              size: 64,
              color: AppColors.error,
            ),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: onRetry,
              child: const Text('Повторить'),
            ),
          ],
        ),
      ),
    );
  }
}
