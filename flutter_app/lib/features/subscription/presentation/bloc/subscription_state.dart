import 'package:equatable/equatable.dart';

import '../../domain/entities/renewal_option.dart';
import '../../domain/entities/subscription.dart';

abstract class SubscriptionState extends Equatable {
  const SubscriptionState();

  @override
  List<Object?> get props => [];
}

/// Initial / idle state.
class SubscriptionInitial extends SubscriptionState {
  const SubscriptionInitial();
}

/// Data is loading.
class SubscriptionLoading extends SubscriptionState {
  const SubscriptionLoading();
}

/// Data loaded successfully.
class SubscriptionLoaded extends SubscriptionState {
  const SubscriptionLoaded({
    required this.subscription,
    required this.renewalOptions,
  });

  /// `null` when the user has no active subscription.
  final Subscription? subscription;
  final List<RenewalOption> renewalOptions;

  @override
  List<Object?> get props => [subscription, renewalOptions];
}

/// An error occurred while loading.
class SubscriptionError extends SubscriptionState {
  const SubscriptionError(this.message);

  final String message;

  @override
  List<Object?> get props => [message];
}
