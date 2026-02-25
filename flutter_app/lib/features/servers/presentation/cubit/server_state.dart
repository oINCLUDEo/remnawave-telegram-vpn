import 'package:equatable/equatable.dart';

import '../../domain/entities/server_category_entity.dart';

abstract class ServerState extends Equatable {
  const ServerState();

  @override
  List<Object?> get props => [];
}

/// Initial / idle state before any load is triggered.
class ServerInitial extends ServerState {
  const ServerInitial();
}

/// API call in progress.
class ServerLoading extends ServerState {
  const ServerLoading();
}

/// Servers loaded successfully.
class ServerLoaded extends ServerState {
  const ServerLoaded({required this.categories});

  final List<ServerCategoryEntity> categories;

  @override
  List<Object?> get props => [categories];
}

/// Loading failed.
class ServerError extends ServerState {
  const ServerError(this.message);

  final String message;

  @override
  List<Object?> get props => [message];
}
