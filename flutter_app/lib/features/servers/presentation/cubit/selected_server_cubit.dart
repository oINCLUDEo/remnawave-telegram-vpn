import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../domain/entities/server_entity.dart';

// ── State ────────────────────────────────────────────────────────────────────

class SelectedServerState extends Equatable {
  final int? id;
  final String name;
  final String flag;
  final String? matchKey;

  const SelectedServerState({
    this.id,
    this.name = '',
    this.flag = '🌐',
    this.matchKey,
  });

  bool get isEmpty => name.isEmpty;

  @override
  List<Object?> get props => [id, name, flag, matchKey];
}

// ── Cubit ────────────────────────────────────────────────────────────────────

class SelectedServerCubit extends Cubit<SelectedServerState> {
  SelectedServerCubit() : super(const SelectedServerState());

  void select(ServerEntity server) {
    final rawName = server.name;
    final parts = rawName.split('—');
    // Heuristic: config remark in v2ray-json usually matches the last part
    // after '—', so we use it as a matching key.
    final keyPart = parts.isNotEmpty ? parts.last.trim() : rawName.trim();
    final flagKey =
        server.flag.trim().isNotEmpty && server.flag.trim() != '🌐'
            ? server.flag.trim()
            : null;

    emit(
      SelectedServerState(
        id: server.id,
        name: server.name,
        flag: server.flag.isEmpty ? '🌐' : server.flag,
        // Prefer matching by flag emoji first (🇪🇪, 🇳🇱, …) since RemnaWave
        // `v2ray-json` configs use it in `remarks`, while server names may
        // contain internal config profile identifiers (e.g. BRIDGE_NL_IN).
        matchKey: flagKey ??
            (server.matchKey?.trim().isNotEmpty == true
                ? server.matchKey
                : keyPart),
      ),
    );
  }

  void clear() => emit(const SelectedServerState());
}
