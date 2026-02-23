import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../../core/providers/subscription_provider.dart';

class SubscriptionScreen extends StatefulWidget {
  const SubscriptionScreen({super.key});

  @override
  State<SubscriptionScreen> createState() => _SubscriptionScreenState();
}

class _SubscriptionScreenState extends State<SubscriptionScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SubscriptionProvider>().loadSubscription();
      context.read<SubscriptionProvider>().loadTariffs();
    });
  }

  void _showQRCode(String config) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('VPN конфигурация'),
        content: SizedBox(
          width: 300,
          height: 300,
          child: QrImageView(
            data: config,
            version: QrVersions.auto,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Закрыть'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final subscription = context.watch<SubscriptionProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Подписка'),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await subscription.loadSubscription();
          await subscription.loadTariffs();
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (subscription.hasActiveSubscription && subscription.subscription != null) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.check_circle, color: Colors.green, size: 32),
                          const SizedBox(width: 16),
                          const Text(
                            'Подписка активна',
                            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      const Divider(height: 24),
                      _buildInfoRow('Истекает', subscription.subscription!['expires_at'] ?? 'N/A'),
                      if (subscription.subscription!['data_limit_gb'] != null)
                        _buildInfoRow(
                          'Трафик',
                          '${subscription.subscription!['data_remaining_gb']?.toStringAsFixed(1) ?? '0'} / ${subscription.subscription!['data_limit_gb']} GB',
                        ),
                      _buildInfoRow('Устройств', '${subscription.subscription!['devices_count']} / ${subscription.subscription!['max_devices']}'),
                      const SizedBox(height: 16),
                      if (subscription.subscription!['config_link'] != null)
                        ElevatedButton.icon(
                          onPressed: () => _showQRCode(subscription.subscription!['config_link']),
                          icon: const Icon(Icons.qr_code),
                          label: const Text('Показать QR код'),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
            ] else ...[
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Column(
                    children: [
                      Icon(Icons.info_outline, size: 48, color: Colors.grey),
                      SizedBox(height: 16),
                      Text(
                        'Нет активной подписки',
                        style: TextStyle(fontSize: 18),
                      ),
                      SizedBox(height: 8),
                      Text('Выберите тариф ниже'),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
            ],
            
            const Text('Доступные тарифы', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            ...subscription.tariffs.map((tariff) => Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                tariff['name'] ?? '',
                                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                              ),
                              if (tariff['description'] != null)
                                Text(tariff['description']),
                            ],
                          ),
                        ),
                        Text(
                          '${(tariff['price_rubles'] ?? 0).toStringAsFixed(2)} ₽',
                          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text('${tariff['period_days']} дней'),
                    if (tariff['data_limit_gb'] != null)
                      Text('${tariff['data_limit_gb']} GB')
                    else
                      const Text('Безлимитный трафик'),
                    Text('До ${tariff['max_devices']} устройств'),
                    const SizedBox(height: 8),
                    ElevatedButton(
                      onPressed: () {
                        // TODO: Server selection and purchase
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Выбор сервера и покупка')),
                        );
                      },
                      child: const Text('Купить'),
                    ),
                  ],
                ),
              ),
            )),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}
