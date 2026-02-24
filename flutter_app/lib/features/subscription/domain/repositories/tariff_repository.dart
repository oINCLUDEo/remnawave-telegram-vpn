import '../../../../core/errors/failures.dart';
import '../entities/tariff_plan.dart';

/// Contract for fetching available subscription tariffs.
abstract class TariffRepository {
  /// Returns the list of available tariff plans from the backend.
  ///
  /// Returns [Right<List<TariffPlan>>] on success.
  /// Returns [Left<Failure>] on network / auth / parse errors.
  Future<({List<TariffPlan> plans, String salesMode})> getPurchaseOptions();
}
