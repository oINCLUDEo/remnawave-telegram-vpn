import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/subscription_provider.dart';
import 'package:intl/intl.dart';

class SubscriptionScreen extends StatelessWidget {
  const SubscriptionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final subscriptionProvider = Provider.of<SubscriptionProvider>(context);
    final subscription = subscriptionProvider.subscription;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Subscription'),
      ),
      body: RefreshIndicator(
        onRefresh: () => subscriptionProvider.refreshSubscription(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(24),
          child: subscription != null
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Status Card
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Column(
                          children: [
                            Icon(
                              subscription.isActive
                                  ? Icons.check_circle
                                  : Icons.cancel,
                              size: 64,
                              color: subscription.isActive
                                  ? Colors.green
                                  : Colors.red,
                            ),
                            const SizedBox(height: 16),
                            Text(
                              subscription.isActive ? 'Active' : 'Inactive',
                              style: Theme.of(context)
                                  .textTheme
                                  .headlineSmall
                                  ?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                            ),
                            if (subscription.isTrial) ...[
                              const SizedBox(height: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 8,
                                ),
                                decoration: BoxDecoration(
                                  color: Colors.blue.withOpacity(0.1),
                                  borderRadius: BorderRadius.circular(20),
                                ),
                                child: const Text(
                                  'Trial Period',
                                  style: TextStyle(
                                    color: Colors.blue,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    // Details Card
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Details',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleLarge
                                  ?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                            ),
                            const SizedBox(height: 16),
                            _buildDetailRow(
                              context,
                              'Start Date',
                              DateFormat('MMM dd, yyyy')
                                  .format(subscription.startDate),
                            ),
                            _buildDetailRow(
                              context,
                              'End Date',
                              DateFormat('MMM dd, yyyy')
                                  .format(subscription.endDate),
                            ),
                            _buildDetailRow(
                              context,
                              'Days Remaining',
                              '${subscription.daysRemaining}',
                            ),
                            const Divider(height: 32),
                            _buildDetailRow(
                              context,
                              'Traffic Limit',
                              '${subscription.trafficLimitGb} GB',
                            ),
                            _buildDetailRow(
                              context,
                              'Traffic Used',
                              '${subscription.trafficUsedGb.toStringAsFixed(2)} GB',
                            ),
                            _buildDetailRow(
                              context,
                              'Traffic Remaining',
                              '${subscription.trafficRemainingGb.toStringAsFixed(2)} GB',
                            ),
                            const SizedBox(height: 12),
                            LinearProgressIndicator(
                              value: subscription.trafficUsagePercent / 100,
                              backgroundColor: Colors.grey[300],
                              borderRadius: BorderRadius.circular(4),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              '${subscription.trafficUsagePercent.toStringAsFixed(1)}% used',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                            const Divider(height: 32),
                            _buildDetailRow(
                              context,
                              'Device Limit',
                              '${subscription.deviceLimit}',
                            ),
                            _buildDetailRow(
                              context,
                              'Auto-pay',
                              subscription.autopayEnabled ? 'Enabled' : 'Disabled',
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    // Configuration Link Card (if available)
                    if (subscription.subscriptionUrl != null &&
                        subscription.subscriptionUrl!.isNotEmpty) ...[
                      Card(
                        child: ListTile(
                          leading: const Icon(Icons.link),
                          title: const Text('Configuration URL'),
                          subtitle: const Text('Tap to copy'),
                          trailing: const Icon(Icons.copy),
                          onTap: () {
                            // Copy to clipboard functionality
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('URL copied to clipboard'),
                              ),
                            );
                          },
                        ),
                      ),
                    ],
                  ],
                )
              : Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.info_outline,
                        size: 64,
                        color: Colors.grey,
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        'No subscription data',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Pull to refresh',
                        style: TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                ),
        ),
      ),
    );
  }

  Widget _buildDetailRow(BuildContext context, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              color: Colors.grey[600],
              fontSize: 14,
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }
}
