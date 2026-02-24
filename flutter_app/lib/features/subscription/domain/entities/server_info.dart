import 'package:equatable/equatable.dart';

/// Info about a VPN server included in a subscription.
class ServerInfo extends Equatable {
  const ServerInfo({
    required this.uuid,
    required this.name,
    this.countryCode,
  });

  final String uuid;
  final String name;
  final String? countryCode;

  @override
  List<Object?> get props => [uuid, name, countryCode];
}
