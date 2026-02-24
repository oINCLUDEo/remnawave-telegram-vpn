import '../../domain/entities/tariff_plan.dart';
import 'tariff_period_model.dart';

/// JSON ↔ [TariffPlan] mapping.
///
/// Backend tariff shape (from /cabinet/subscription/purchase-options):
/// ```json
/// {
///   "id": 1,
///   "name": "Premium",
///   "description": null,
///   "tier_level": 2,
///   "is_available": true,
///   "periods": [ ... ]
/// }
/// ```
class TariffPlanModel extends TariffPlan {
  const TariffPlanModel({
    required super.id,
    required super.name,
    super.description,
    required super.tierLevel,
    required super.periods,
  });

  factory TariffPlanModel.fromJson(Map<String, dynamic> json) {
    final rawPeriods = json['periods'] as List<dynamic>? ?? [];
    final periods = rawPeriods
        .whereType<Map<String, dynamic>>()
        .map(TariffPeriodModel.fromJson)
        .toList();

    return TariffPlanModel(
      id: (json['id'] as num).toInt(),
      name: json['name'] as String? ?? 'Тариф',
      description: json['description'] as String?,
      tierLevel: (json['tier_level'] as num?)?.toInt() ?? 1,
      periods: periods,
    );
  }
}
