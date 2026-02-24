import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:get_it/get_it.dart';

import '../network/api_client.dart';
import '../storage/secure_storage_service.dart';
import '../../features/auth/data/datasources/auth_remote_datasource.dart';
import '../../features/auth/data/repositories/auth_repository_impl.dart';
import '../../features/auth/domain/repositories/auth_repository.dart';
import '../../features/auth/domain/usecases/login_usecase.dart';
import '../../features/auth/domain/usecases/register_usecase.dart';
import '../../features/auth/presentation/bloc/auth_bloc.dart';
import '../../features/subscription/data/datasources/tariff_remote_datasource.dart';
import '../../features/subscription/data/repositories/tariff_repository_impl.dart';
import '../../features/subscription/domain/repositories/tariff_repository.dart';
import '../../features/subscription/presentation/cubit/tariff_cubit.dart';

final sl = GetIt.instance;

/// Register all dependencies.  Call once in [main].
void setupDependencies({String? baseUrl}) {
  // Core
  sl.registerLazySingleton<FlutterSecureStorage>(
    () => const FlutterSecureStorage(),
  );
  sl.registerLazySingleton<SecureStorageService>(
    () => SecureStorageService(sl<FlutterSecureStorage>()),
  );
  sl.registerLazySingleton<ApiClient>(() {
    final client = ApiClient(storage: sl<SecureStorageService>(), baseUrl: baseUrl);
    client.attachInterceptors();
    return client;
  });

  // Auth — data
  sl.registerLazySingleton<AuthRemoteDataSource>(
    () => AuthRemoteDataSource(
      apiClient: sl<ApiClient>(),
      storage: sl<SecureStorageService>(),
    ),
  );
  sl.registerLazySingleton<AuthRepository>(
    () => AuthRepositoryImpl(
      remoteDataSource: sl<AuthRemoteDataSource>(),
      storage: sl<SecureStorageService>(),
    ),
  );

  // Auth — domain
  sl.registerLazySingleton<LoginUseCase>(
    () => LoginUseCase(sl<AuthRepository>()),
  );
  sl.registerLazySingleton<RegisterUseCase>(
    () => RegisterUseCase(sl<AuthRepository>()),
  );

  // Auth — presentation
  sl.registerFactory<AuthBloc>(
    () => AuthBloc(
      loginUseCase: sl<LoginUseCase>(),
      registerUseCase: sl<RegisterUseCase>(),
      authRepository: sl<AuthRepository>(),
    ),
  );

  // Subscription / Tariffs — data
  sl.registerLazySingleton<TariffRemoteDataSource>(
    () => TariffRemoteDataSource(apiClient: sl<ApiClient>()),
  );
  sl.registerLazySingleton<TariffRepository>(
    () => TariffRepositoryImpl(dataSource: sl<TariffRemoteDataSource>()),
  );

  // Subscription / Tariffs — presentation
  sl.registerFactory<TariffCubit>(
    () => TariffCubit(repository: sl<TariffRepository>()),
  );
}
