import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../core/api/api_client.dart';

class ReferralScreen extends StatefulWidget {
  const ReferralScreen({super.key});

  @override
  State<ReferralScreen> createState() => _ReferralScreenState();
}

class _ReferralScreenState extends State<ReferralScreen> {
  final _api = ApiClient();
  Map<String, dynamic>? _stats;
  List<dynamic> _referrals = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      final stats = await _api.getReferralStats();
      final refs = await _api.getReferrals();
      setState(() {
        _stats = stats;
        _referrals = refs;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка: ${e.toString()}')),
        );
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _copyReferralLink() {
    if (_stats != null) {
      Clipboard.setData(ClipboardData(text: _stats!['referral_link']));
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ссылка скопирована')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Рефералы'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadData,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (_stats != null) ...[
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          children: [
                            const Text('Ваш реферальный код', style: TextStyle(fontSize: 16)),
                            const SizedBox(height: 8),
                            Text(
                              _stats!['referral_code'] ?? '',
                              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                            ),
                            const SizedBox(height: 16),
                            ElevatedButton.icon(
                              onPressed: _copyReferralLink,
                              icon: const Icon(Icons.copy),
                              label: const Text('Скопировать ссылку'),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: Card(
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                children: [
                                  const Text('Рефералов'),
                                  const SizedBox(height: 8),
                                  Text(
                                    '${_stats!['total_referrals'] ?? 0}',
                                    style: const TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Card(
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                children: [
                                  const Text('Заработано'),
                                  const SizedBox(height: 8),
                                  Text(
                                    '${(_stats!['total_earned_rubles'] ?? 0).toStringAsFixed(0)} ₽',
                                    style: const TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    const Text('Ваши рефералы', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                  ],
                  ..._referrals.map((ref) => Card(
                    child: ListTile(
                      leading: const CircleAvatar(child: Icon(Icons.person)),
                      title: Text(ref['first_name'] ?? 'Пользователь'),
                      subtitle: Text('Заработано: ${(ref['earned_from_user_rubles'] ?? 0).toStringAsFixed(2)} ₽'),
                      trailing: Icon(
                        ref['has_subscription'] ? Icons.check_circle : Icons.circle_outlined,
                        color: ref['has_subscription'] ? Colors.green : Colors.grey,
                      ),
                    ),
                  )),
                ],
              ),
            ),
    );
  }
}
