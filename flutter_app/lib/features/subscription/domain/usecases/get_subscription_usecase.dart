import '../entities/subscription.dart';
import '../repositories/subscription_repository.dart';

/// Fetches the current user's subscription.
class GetSubscriptionUseCase {
  const GetSubscriptionUseCase(this._repository);

  final SubscriptionRepository _repository;

  Future<Subscription?> call() => _repository.getSubscription();
}
