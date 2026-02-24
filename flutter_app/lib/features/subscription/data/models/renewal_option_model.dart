import '../../domain/entities/renewal_option.dart';

/// JSON ↔ [RenewalOption] mapping.
class RenewalOptionModel extends RenewalOption {
  const RenewalOptionModel({
    required super.periodDays,
    required super.priceKopeks,
    required super.priceRubles,
    super.discountPercent,
    super.originalPriceKopeks,
  });

  factory RenewalOptionModel.fromJson(Map<String, dynamic> json) =>
      RenewalOptionModel(
        periodDays: json['period_days'] as int,
        priceKopeks: json['price_kopeks'] as int,
        priceRubles: ((json['price_rubles'] as num?) ?? 0).toDouble(),
        discountPercent: (json['discount_percent'] as int?) ?? 0,
        originalPriceKopeks: json['original_price_kopeks'] as int?,
      );
}
