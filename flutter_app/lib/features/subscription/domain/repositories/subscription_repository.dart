import '../entities/renewal_option.dart';
import '../entities/subscription.dart';

/// Abstract repository for subscription data.
abstract class SubscriptionRepository {
  /// Returns the current user's subscription status.
  /// Returns `null` if the user has no active subscription.
  Future<Subscription?> getSubscription();

  /// Returns available renewal options for the current subscription.
  Future<List<RenewalOption>> getRenewalOptions();
}
