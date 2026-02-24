import 'package:equatable/equatable.dart';
import '../../domain/entities/tariff_period.dart';
import '../../domain/entities/tariff_plan.dart';

abstract class TariffState extends Equatable {
  const TariffState();

  @override
  List<Object?> get props => [];
}

/// Initial / idle state before loading starts.
class TariffInitial extends TariffState {
  const TariffInitial();
}

/// API call in progress.
class TariffLoading extends TariffState {
  const TariffLoading();
}

/// Plans loaded successfully.
class TariffLoaded extends TariffState {
  const TariffLoaded({
    required this.plans,
    required this.salesMode,
    required this.selectedPlanIndex,
    required this.selectedPeriodIndex,
  });

  final List<TariffPlan> plans;
  final String salesMode;

  /// Index of the active tariff plan in [plans].
  final int selectedPlanIndex;

  /// Index of the active period within the selected plan's periods.
  final int selectedPeriodIndex;

  TariffPlan get selectedPlan => plans[selectedPlanIndex];
  List<TariffPeriod> get periods => selectedPlan.periods;

  TariffLoaded copyWith({
    List<TariffPlan>? plans,
    String? salesMode,
    int? selectedPlanIndex,
    int? selectedPeriodIndex,
  }) {
    return TariffLoaded(
      plans: plans ?? this.plans,
      salesMode: salesMode ?? this.salesMode,
      selectedPlanIndex: selectedPlanIndex ?? this.selectedPlanIndex,
      selectedPeriodIndex: selectedPeriodIndex ?? this.selectedPeriodIndex,
    );
  }

  @override
  List<Object?> get props =>
      [plans, salesMode, selectedPlanIndex, selectedPeriodIndex];
}

/// Loading failed.
class TariffError extends TariffState {
  const TariffError(this.message);
  final String message;

  @override
  List<Object?> get props => [message];
}
