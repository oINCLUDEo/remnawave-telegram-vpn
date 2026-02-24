import '../entities/renewal_option.dart';
import '../repositories/subscription_repository.dart';

/// Fetches available renewal options for the current subscription.
class GetRenewalOptionsUseCase {
  const GetRenewalOptionsUseCase(this._repository);

  final SubscriptionRepository _repository;

  Future<List<RenewalOption>> call() => _repository.getRenewalOptions();
}
