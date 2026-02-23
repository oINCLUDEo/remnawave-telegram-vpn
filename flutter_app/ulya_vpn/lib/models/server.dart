class VPNServer {
  final String id;
  final String name;
  final String country;
  final String? countryCode;
  final String? city;
  final String address;
  final int port;
  final bool isActive;
  final int? ping;
  final int? load;

  VPNServer({
    required this.id,
    required this.name,
    required this.country,
    this.countryCode,
    this.city,
    required this.address,
    required this.port,
    required this.isActive,
    this.ping,
    this.load,
  });

  factory VPNServer.fromJson(Map<String, dynamic> json) {
    return VPNServer(
      id: json['id'] as String,
      name: json['name'] as String,
      country: json['country'] as String,
      countryCode: json['country_code'] as String?,
      city: json['city'] as String?,
      address: json['address'] as String,
      port: json['port'] as int,
      isActive: json['is_active'] as bool? ?? true,
      ping: json['ping'] as int?,
      load: json['load'] as int?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'country': country,
      'country_code': countryCode,
      'city': city,
      'address': address,
      'port': port,
      'is_active': isActive,
      'ping': ping,
      'load': load,
    };
  }

  String get displayLocation {
    if (city != null && city!.isNotEmpty) {
      return '$city, $country';
    }
    return country;
  }
}
