import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

// ── State ────────────────────────────────────────────────────────────────────

class SelectedServerState extends Equatable {
  final String name;
  final String flag;

  const SelectedServerState({this.name = '', this.flag = '🌐'});

  bool get isEmpty => name.isEmpty;

  @override
  List<Object?> get props => [name, flag];
}

// ── Cubit ────────────────────────────────────────────────────────────────────

class SelectedServerCubit extends Cubit<SelectedServerState> {
  SelectedServerCubit() : super(const SelectedServerState());

  void select(String name, String flag) =>
      emit(SelectedServerState(name: name, flag: flag.isEmpty ? '🌐' : flag));

  void clear() => emit(const SelectedServerState());
}
