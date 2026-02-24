import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/errors/failures.dart';
import '../../domain/usecases/get_renewal_options_usecase.dart';
import '../../domain/usecases/get_subscription_usecase.dart';
import 'subscription_event.dart';
import 'subscription_state.dart';

/// BLoC for fetching and managing subscription data.
class SubscriptionBloc extends Bloc<SubscriptionEvent, SubscriptionState> {
  SubscriptionBloc({
    required GetSubscriptionUseCase getSubscription,
    required GetRenewalOptionsUseCase getRenewalOptions,
  })  : _getSubscription = getSubscription,
        _getRenewalOptions = getRenewalOptions,
        super(const SubscriptionInitial()) {
    on<SubscriptionLoadRequested>(_onLoad);
    on<SubscriptionRefreshRequested>(_onRefresh);
  }

  final GetSubscriptionUseCase _getSubscription;
  final GetRenewalOptionsUseCase _getRenewalOptions;

  Future<void> _onLoad(
    SubscriptionLoadRequested event,
    Emitter<SubscriptionState> emit,
  ) async {
    emit(const SubscriptionLoading());
    await _fetch(emit);
  }

  Future<void> _onRefresh(
    SubscriptionRefreshRequested event,
    Emitter<SubscriptionState> emit,
  ) async {
    await _fetch(emit);
  }

  Future<void> _fetch(Emitter<SubscriptionState> emit) async {
    try {
      final subFuture = _getSubscription();
      final optsFuture = _getRenewalOptions();
      final subscription = await subFuture;
      final renewalOptions = await optsFuture;
      emit(SubscriptionLoaded(
        subscription: subscription,
        renewalOptions: renewalOptions,
      ));
    } on Failure catch (f) {
      emit(SubscriptionError(f.message));
    } catch (_) {
      emit(const SubscriptionError('Не удалось загрузить данные подписки'));
    }
  }
}
