import '../../domain/entities/auth_tokens.dart';
import 'user_model.dart';

/// JSON ↔ [AuthTokens] mapping.
///
/// Matches the backend `AuthResponse` schema.
class AuthResponseModel extends AuthTokens {
  const AuthResponseModel({
    required super.accessToken,
    required super.refreshToken,
    required super.expiresIn,
    required super.user,
  });

  factory AuthResponseModel.fromJson(Map<String, dynamic> json) =>
      AuthResponseModel(
        accessToken: json['access_token'] as String,
        refreshToken: json['refresh_token'] as String,
        expiresIn: json['expires_in'] as int,
        user: UserModel.fromJson(json['user'] as Map<String, dynamic>),
      );
}
