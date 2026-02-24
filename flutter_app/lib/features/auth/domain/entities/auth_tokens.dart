import 'package:equatable/equatable.dart';

import 'user.dart';

/// JWT token pair returned by the backend on successful auth.
class AuthTokens extends Equatable {
  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    required this.expiresIn,
    required this.user,
  });

  final String accessToken;
  final String refreshToken;

  /// Access token lifetime in seconds.
  final int expiresIn;

  final User user;

  @override
  List<Object?> get props => [accessToken, refreshToken, expiresIn, user];
}
