import 'package:equatable/equatable.dart';
import 'server_entity.dart';

/// A named group of servers shown as a collapsible section in the app.
class ServerCategoryEntity extends Equatable {
  const ServerCategoryEntity({
    required this.id,
    required this.name,
    required this.subtitle,
    required this.serverCount,
    required this.servers,
  });

  /// Category slug matching [ServerEntity.category].
  final String id;

  /// Display name, e.g. "Белые списки".
  final String name;

  /// One-liner description shown below the title, e.g. "Для доступа везде".
  final String subtitle;

  final int serverCount;
  final List<ServerEntity> servers;

  @override
  List<Object?> get props => [id, name, subtitle, serverCount, servers];
}
