class User {
  final int id;
  final int? telegramId;
  final String? username;
  final String? firstName;
  final String? lastName;
  final String? email;
  final String status;
  final String language;
  final int balanceKopeks;
  final double balanceRubles;
  final String? referralCode;
  final DateTime createdAt;
  final DateTime updatedAt;

  User({
    required this.id,
    this.telegramId,
    this.username,
    this.firstName,
    this.lastName,
    this.email,
    required this.status,
    required this.language,
    required this.balanceKopeks,
    required this.balanceRubles,
    this.referralCode,
    required this.createdAt,
    required this.updatedAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as int,
      telegramId: json['telegram_id'] as int?,
      username: json['username'] as String?,
      firstName: json['first_name'] as String?,
      lastName: json['last_name'] as String?,
      email: json['email'] as String?,
      status: json['status'] as String,
      language: json['language'] as String,
      balanceKopeks: json['balance_kopeks'] as int,
      balanceRubles: (json['balance_rubles'] as num).toDouble(),
      referralCode: json['referral_code'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'telegram_id': telegramId,
      'username': username,
      'first_name': firstName,
      'last_name': lastName,
      'email': email,
      'status': status,
      'language': language,
      'balance_kopeks': balanceKopeks,
      'balance_rubles': balanceRubles,
      'referral_code': referralCode,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  String get displayName {
    if (firstName != null && firstName!.isNotEmpty) {
      return lastName != null && lastName!.isNotEmpty
          ? '$firstName $lastName'
          : firstName!;
    }
    if (username != null && username!.isNotEmpty) {
      return '@$username';
    }
    if (email != null && email!.isNotEmpty) {
      return email!;
    }
    return 'User #$id';
  }
}
