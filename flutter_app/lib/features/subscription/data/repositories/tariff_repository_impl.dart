import 'package:dio/dio.dart';

import '../../../../core/errors/failures.dart';
import '../../domain/entities/tariff_plan.dart';
import '../../domain/repositories/tariff_repository.dart';
import '../datasources/tariff_remote_datasource.dart';

class TariffRepositoryImpl implements TariffRepository {
  const TariffRepositoryImpl({required TariffRemoteDataSource dataSource})
      : _dataSource = dataSource;

  final TariffRemoteDataSource _dataSource;

  @override
  Future<({List<TariffPlan> plans, String salesMode})>
      getPurchaseOptions() async {
    try {
      final result = await _dataSource.getPurchaseOptions();
      return (
        plans: List<TariffPlan>.from(result.plans),
        salesMode: result.salesMode,
      );
    } on DioException catch (e) {
      final statusCode = e.response?.statusCode;
      if (statusCode == 401 || statusCode == 403) {
        throw const TokenExpiredFailure();
      }
      if (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.receiveTimeout) {
        throw const NetworkFailure();
      }
      final message = e.response?.data?['detail']?.toString() ??
          e.message ??
          'Ошибка загрузки тарифов';
      throw ServerFailure(message, statusCode: statusCode);
    }
  }
}
