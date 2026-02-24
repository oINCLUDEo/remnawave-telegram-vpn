import '../../domain/entities/user.dart';

/// JSON ↔ [User] mapping.
class UserModel extends User {
  const UserModel({
    required super.id,
    required super.createdAt,
    super.telegramId,
    super.username,
    super.firstName,
    super.lastName,
    super.email,
    super.emailVerified,
    super.balanceKopeks,
    super.referralCode,
    super.language,
    super.authType,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) => UserModel(
        id: json['id'] as int,
        telegramId: json['telegram_id'] as int?,
        username: json['username'] as String?,
        firstName: json['first_name'] as String?,
        lastName: json['last_name'] as String?,
        email: json['email'] as String?,
        emailVerified: (json['email_verified'] as bool?) ?? false,
        balanceKopeks: (json['balance_kopeks'] as int?) ?? 0,
        referralCode: json['referral_code'] as String?,
        language: (json['language'] as String?) ?? 'ru',
        createdAt: DateTime.parse(json['created_at'] as String),
        authType: (json['auth_type'] as String?) ?? 'email',
      );
}
