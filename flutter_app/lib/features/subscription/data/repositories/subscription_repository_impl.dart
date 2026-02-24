import '../../domain/entities/renewal_option.dart';
import '../../domain/entities/subscription.dart';
import '../../domain/repositories/subscription_repository.dart';
import '../datasources/subscription_remote_datasource.dart';

/// Concrete implementation of [SubscriptionRepository].
class SubscriptionRepositoryImpl implements SubscriptionRepository {
  const SubscriptionRepositoryImpl({
    required SubscriptionRemoteDataSource remoteDataSource,
  }) : _remote = remoteDataSource;

  final SubscriptionRemoteDataSource _remote;

  @override
  Future<Subscription?> getSubscription() => _remote.getSubscription();

  @override
  Future<List<RenewalOption>> getRenewalOptions() =>
      _remote.getRenewalOptions();
}
