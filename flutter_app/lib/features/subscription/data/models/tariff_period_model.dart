import '../../domain/entities/tariff_period.dart';

/// JSON ↔ [TariffPeriod] mapping for a single billing period.
///
/// Backend period shape (from /cabinet/subscription/purchase-options):
/// ```json
/// {
///   "days": 30,
///   "months": 1,
///   "label": "1 месяц",
///   "price_label": "299 ₽",
///   "price_per_month_label": "299 ₽/мес",
///   "discount_percent": 16   // optional
/// }
/// ```
class TariffPeriodModel extends TariffPeriod {
  const TariffPeriodModel({
    required super.days,
    required super.months,
    required super.label,
    required super.priceLabel,
    required super.pricePerMonthLabel,
    super.discountPercent,
  });

  factory TariffPeriodModel.fromJson(Map<String, dynamic> json) {
    return TariffPeriodModel(
      days: (json['days'] as num).toInt(),
      months: (json['months'] as num).toInt(),
      label: json['label'] as String? ?? '${json['days']} дн.',
      priceLabel: json['price_label'] as String? ?? '',
      pricePerMonthLabel: json['price_per_month_label'] as String? ?? '',
      discountPercent: json['discount_percent'] != null
          ? (json['discount_percent'] as num).toInt()
          : null,
    );
  }
}
