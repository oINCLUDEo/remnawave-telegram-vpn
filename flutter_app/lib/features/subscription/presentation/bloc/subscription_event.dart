import 'package:equatable/equatable.dart';

abstract class SubscriptionEvent extends Equatable {
  const SubscriptionEvent();

  @override
  List<Object?> get props => [];
}

/// Triggered when the subscription screen is opened or refreshed.
class SubscriptionLoadRequested extends SubscriptionEvent {
  const SubscriptionLoadRequested();
}

/// Triggered when the user pulls to refresh.
class SubscriptionRefreshRequested extends SubscriptionEvent {
  const SubscriptionRefreshRequested();
}
