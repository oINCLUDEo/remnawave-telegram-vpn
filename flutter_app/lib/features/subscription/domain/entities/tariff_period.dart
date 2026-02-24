import 'package:equatable/equatable.dart';

/// A single purchasable period within a tariff (e.g. 1 month / 3 months).
class TariffPeriod extends Equatable {
  const TariffPeriod({
    required this.days,
    required this.months,
    required this.label,
    required this.priceLabel,
    required this.pricePerMonthLabel,
    this.discountPercent,
  });

  /// Duration in days.
  final int days;

  /// Approximate months (days ÷ 30).
  final int months;

  /// Human-readable duration label, e.g. "1 месяц".
  final String label;

  /// Formatted total price, e.g. "299 ₽".
  final String priceLabel;

  /// Formatted price per month, e.g. "299 ₽/мес".
  final String pricePerMonthLabel;

  /// Discount percentage if applicable, e.g. 16 for "-16%".
  final int? discountPercent;

  @override
  List<Object?> get props => [
        days,
        months,
        label,
        priceLabel,
        pricePerMonthLabel,
        discountPercent,
      ];
}
