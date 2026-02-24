import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/errors/failures.dart';
import '../../domain/repositories/tariff_repository.dart';
import 'tariff_state.dart';

class TariffCubit extends Cubit<TariffState> {
  TariffCubit({required TariffRepository repository})
      : _repository = repository,
        super(const TariffInitial());

  final TariffRepository _repository;

  /// Fetch purchase options from the API and emit the appropriate state.
  ///
  /// Auth is handled transparently by the datasource:
  ///   • With a valid token → authenticated endpoint (promo-group discounts applied)
  ///   • Without a valid token → public endpoint (base prices, no discounts)
  Future<void> loadTariffs() async {
    emit(const TariffLoading());
    try {
      final result = await _repository.getPurchaseOptions();

      if (result.plans.isEmpty) {
        emit(const TariffError('Нет доступных тарифов'));
        return;
      }

      emit(TariffLoaded(
        plans: result.plans,
        salesMode: result.salesMode,
        selectedPlanIndex: 0,
        // Pre-select the second period (index 1) if available, else 0
        selectedPeriodIndex:
            result.plans.first.periods.length > 1 ? 1 : 0,
      ));
    } on NetworkFailure catch (e) {
      emit(TariffError(e.message));
    } on Failure catch (e) {
      emit(TariffError(e.message));
    } catch (_) {
      emit(const TariffError('Не удалось загрузить тарифы'));
    }
  }

  /// Change the selected plan (when multiple plans are available).
  void selectPlan(int planIndex) {
    final current = state;
    if (current is! TariffLoaded) return;
    emit(current.copyWith(
      selectedPlanIndex: planIndex,
      selectedPeriodIndex: 0,
    ));
  }

  /// Change the selected period within the current plan.
  void selectPeriod(int periodIndex) {
    final current = state;
    if (current is! TariffLoaded) return;
    emit(current.copyWith(selectedPeriodIndex: periodIndex));
  }
}
