import 'package:dio/dio.dart';

import '../../../../core/errors/failures.dart';
import '../../domain/entities/server_category_entity.dart';
import '../../domain/repositories/server_repository.dart';
import '../datasources/server_remote_datasource.dart';

class ServerRepositoryImpl implements ServerRepository {
  const ServerRepositoryImpl({required ServerRemoteDataSource dataSource})
      : _dataSource = dataSource;

  final ServerRemoteDataSource _dataSource;

  @override
  Future<List<ServerCategoryEntity>> getServers() async {
    try {
      return await _dataSource.getServers();
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.receiveTimeout) {
        throw const NetworkFailure();
      }
      final message = e.response?.data?['detail']?.toString() ??
          e.message ??
          'Ошибка загрузки серверов';
      throw ServerFailure(message, statusCode: e.response?.statusCode);
    }
  }
}
