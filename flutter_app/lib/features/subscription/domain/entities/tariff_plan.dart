import 'package:equatable/equatable.dart';
import 'tariff_period.dart';

/// A subscription plan (tariff) with one or more purchasable periods.
class TariffPlan extends Equatable {
  const TariffPlan({
    required this.id,
    required this.name,
    this.description,
    required this.tierLevel,
    required this.periods,
  });

  final int id;
  final String name;
  final String? description;

  /// Tier level (1 = basic, higher = premium).
  final int tierLevel;

  /// Available billing periods, sorted by duration ascending.
  final List<TariffPeriod> periods;

  @override
  List<Object?> get props => [id, name, description, tierLevel, periods];
}
