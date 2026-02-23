import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/providers/balance_provider.dart';

class BalanceScreen extends StatefulWidget {
  const BalanceScreen({super.key});

  @override
  State<BalanceScreen> createState() => _BalanceScreenState();
}

class _BalanceScreenState extends State<BalanceScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<BalanceProvider>().loadBalance();
      context.read<BalanceProvider>().loadTransactions();
    });
  }

  Future<void> _showTopUpDialog() async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Пополнение баланса'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: 'Сумма (₽)',
                hintText: '500',
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),
            const Text('Метод оплаты: YooKassa СБП'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Отмена'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('Пополнить'),
          ),
        ],
      ),
    );

    if (result != null && result.isNotEmpty) {
      final amount = double.tryParse(result);
      if (amount != null && amount > 0) {
        await _topUp(amount);
      }
    }
  }

  Future<void> _topUp(double amount) async {
    try {
      final url = await context.read<BalanceProvider>().topUp(amount, 'YOOKASSA_SBP');
      if (url.isNotEmpty && mounted) {
        await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка: ${e.toString()}')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final balance = context.watch<BalanceProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Баланс'),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await balance.loadBalance();
          await balance.loadTransactions();
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  children: [
                    const Text('Текущий баланс', style: TextStyle(fontSize: 16)),
                    const SizedBox(height: 8),
                    Text(
                      '${balance.balance.toStringAsFixed(2)} ₽',
                      style: const TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton.icon(
                      onPressed: _showTopUpDialog,
                      icon: const Icon(Icons.add),
                      label: const Text('Пополнить'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            const Text('История транзакций', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            ...balance.transactions.map((t) => Card(
              child: ListTile(
                leading: Icon(
                  t['amount_kopeks'] > 0 ? Icons.add_circle : Icons.remove_circle,
                  color: t['amount_kopeks'] > 0 ? Colors.green : Colors.red,
                ),
                title: Text(t['description'] ?? 'Транзакция'),
                subtitle: Text(t['created_at'] ?? ''),
                trailing: Text(
                  '${(t['amount_rubles'] ?? 0).toStringAsFixed(2)} ₽',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: t['amount_kopeks'] > 0 ? Colors.green : Colors.red,
                  ),
                ),
              ),
            )),
          ],
        ),
      ),
    );
  }
}
