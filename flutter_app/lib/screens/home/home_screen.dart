import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/providers/subscription_provider.dart';
import '../../core/providers/balance_provider.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SubscriptionProvider>().loadSubscription();
      context.read<BalanceProvider>().loadBalance();
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final subscription = context.watch<SubscriptionProvider>();
    final balance = context.watch<BalanceProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('VPN Service'),
        actions: [
          IconButton(
            icon: const Icon(Icons.person),
            onPressed: () => context.push('/profile'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await Future.wait([
            subscription.loadSubscription(),
            balance.loadBalance(),
          ]);
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // User Card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    const CircleAvatar(
                      radius: 30,
                      child: Icon(Icons.person, size: 30),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            auth.user?['first_name'] ?? 'Пользователь',
                            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                          ),
                          Text(auth.user?['email'] ?? ''),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            
            // Balance Card
            Card(
              child: InkWell(
                onTap: () => context.push('/balance'),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      const Icon(Icons.account_balance_wallet, size: 40),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Баланс', style: TextStyle(fontSize: 16)),
                            Text(
                              '${balance.balance.toStringAsFixed(2)} ₽',
                              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                      ),
                      const Icon(Icons.chevron_right),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            
            // Subscription Card
            Card(
              child: InkWell(
                onTap: () => context.push('/subscription'),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.vpn_lock, size: 40),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text('Подписка', style: TextStyle(fontSize: 16)),
                                Text(
                                  subscription.hasActiveSubscription ? 'Активна' : 'Нет подписки',
                                  style: TextStyle(
                                    fontSize: 20,
                                    fontWeight: FontWeight.bold,
                                    color: subscription.hasActiveSubscription ? Colors.green : Colors.grey,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const Icon(Icons.chevron_right),
                        ],
                      ),
                      if (subscription.hasActiveSubscription && subscription.subscription != null) ...[
                        const Divider(height: 24),
                        Text('Истекает: ${subscription.subscription!['expires_at'] ?? 'N/A'}'),
                        if (subscription.subscription!['data_limit_gb'] != null)
                          Text('Трафик: ${subscription.subscription!['data_remaining_gb']?.toStringAsFixed(1) ?? '0'} / ${subscription.subscription!['data_limit_gb']} GB'),
                      ],
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            
            // Referral Card
            Card(
              child: InkWell(
                onTap: () => context.push('/referral'),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      const Icon(Icons.people, size: 40),
                      const SizedBox(width: 16),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Реферальная программа', style: TextStyle(fontSize: 16)),
                            Text('Приглашай друзей и зарабатывай'),
                          ],
                        ),
                      ),
                      const Icon(Icons.chevron_right),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
