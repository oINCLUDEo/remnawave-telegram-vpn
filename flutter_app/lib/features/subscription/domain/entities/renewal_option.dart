import 'package:equatable/equatable.dart';

/// A subscription renewal option returned by the backend.
class RenewalOption extends Equatable {
  const RenewalOption({
    required this.periodDays,
    required this.priceKopeks,
    required this.priceRubles,
    this.discountPercent = 0,
    this.originalPriceKopeks,
  });

  final int periodDays;
  final int priceKopeks;
  final double priceRubles;
  final int discountPercent;
  final int? originalPriceKopeks;

  bool get hasDiscount => discountPercent > 0;

  /// Display label, e.g. "1 месяц", "3 месяца", "12 месяцев".
  String get periodLabel {
    if (periodDays >= 365) return '${periodDays ~/ 365} год';
    if (periodDays >= 30) {
      final months = periodDays ~/ 30;
      if (months == 1) return '1 месяц';
      if (months < 5) return '$months месяца';
      return '$months месяцев';
    }
    return '$periodDays дней';
  }

  @override
  List<Object?> get props =>
      [periodDays, priceKopeks, priceRubles, discountPercent, originalPriceKopeks];
}
