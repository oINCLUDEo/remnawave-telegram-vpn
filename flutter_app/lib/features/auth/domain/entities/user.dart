import 'package:equatable/equatable.dart';

/// Core user entity — backend `UserResponse` schema.
class User extends Equatable {
  const User({
    required this.id,
    required this.createdAt,
    this.telegramId,
    this.username,
    this.firstName,
    this.lastName,
    this.email,
    this.emailVerified = false,
    this.balanceKopeks = 0,
    this.referralCode,
    this.language = 'ru',
    this.authType = 'email',
  });

  final int id;
  final int? telegramId;
  final String? username;
  final String? firstName;
  final String? lastName;
  final String? email;
  final bool emailVerified;
  final int balanceKopeks;
  double get balanceRubles => balanceKopeks / 100.0;
  final String? referralCode;
  final String language;
  final DateTime createdAt;
  final String authType;

  @override
  List<Object?> get props => [
        id,
        telegramId,
        username,
        firstName,
        lastName,
        email,
        emailVerified,
        balanceKopeks,
        referralCode,
        language,
        createdAt,
        authType,
      ];
}
