import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/errors/failures.dart';
import '../../domain/repositories/server_repository.dart';
import 'server_state.dart';

class ServerCubit extends Cubit<ServerState> {
  ServerCubit({required ServerRepository repository})
      : _repository = repository,
        super(const ServerInitial());

  final ServerRepository _repository;

  Future<void> loadServers() async {
    emit(const ServerLoading());
    try {
      final categories = await _repository.getServers();
      emit(ServerLoaded(categories: categories));
    } on Failure catch (e) {
      emit(ServerError(e.message));
    } catch (e) {
      emit(ServerError(e.toString()));
    }
  }
}
