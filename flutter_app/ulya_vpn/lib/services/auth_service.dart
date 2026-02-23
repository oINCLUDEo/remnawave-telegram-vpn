import 'dart:convert';
import '../config/api_config.dart';
import '../models/user.dart';
import 'api_service.dart';
import 'storage_service.dart';

class AuthService {
  // Login with email/password
  static Future<AuthResult> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await ApiService.post(
        ApiConfig.authLogin,
        {
          'email': email,
          'password': password,
        },
        auth: false,
      );

      final data = ApiService.parseResponse(response);
      
      final accessToken = data['access_token'] as String;
      final refreshToken = data['refresh_token'] as String;
      final userData = data['user'] as Map<String, dynamic>;
      
      await StorageService.saveTokens(
        accessToken: accessToken,
        refreshToken: refreshToken,
      );
      
      final user = User.fromJson(userData);
      await StorageService.saveUserId(user.id);
      
      return AuthResult(success: true, user: user);
    } on ApiException catch (e) {
      return AuthResult(success: false, error: e.message);
    } catch (e) {
      return AuthResult(success: false, error: 'Connection error: $e');
    }
  }

  // Register with email/password
  static Future<AuthResult> register({
    required String email,
    required String password,
    required String firstName,
    String? lastName,
    String language = 'ru',
  }) async {
    try {
      final response = await ApiService.post(
        ApiConfig.authRegister,
        {
          'email': email,
          'password': password,
          'first_name': firstName,
          if (lastName != null) 'last_name': lastName,
          'language': language,
        },
        auth: false,
      );

      final data = ApiService.parseResponse(response);
      
      final accessToken = data['access_token'] as String;
      final refreshToken = data['refresh_token'] as String;
      final userData = data['user'] as Map<String, dynamic>;
      
      await StorageService.saveTokens(
        accessToken: accessToken,
        refreshToken: refreshToken,
      );
      
      final user = User.fromJson(userData);
      await StorageService.saveUserId(user.id);
      
      return AuthResult(success: true, user: user);
    } on ApiException catch (e) {
      return AuthResult(success: false, error: e.message);
    } catch (e) {
      return AuthResult(success: false, error: 'Connection error: $e');
    }
  }

  // Refresh access token
  static Future<bool> refreshToken() async {
    try {
      final refreshToken = await StorageService.getRefreshToken();
      if (refreshToken == null) {
        return false;
      }

      final response = await ApiService.post(
        ApiConfig.authRefresh,
        {'refresh_token': refreshToken},
        auth: false,
      );

      final data = ApiService.parseResponse(response);
      
      final newAccessToken = data['access_token'] as String;
      final newRefreshToken = data['refresh_token'] as String;
      
      await StorageService.saveTokens(
        accessToken: newAccessToken,
        refreshToken: newRefreshToken,
      );
      
      return true;
    } catch (e) {
      return false;
    }
  }

  // Logout
  static Future<void> logout() async {
    await StorageService.clearAll();
  }

  // Check if user is logged in
  static Future<bool> isLoggedIn() async {
    final token = await StorageService.getAccessToken();
    return token != null;
  }

  // Get current user
  static Future<User?> getCurrentUser() async {
    try {
      final response = await ApiService.get(ApiConfig.usersMe);
      final data = ApiService.parseResponse(response);
      return User.fromJson(data);
    } catch (e) {
      return null;
    }
  }
}

class AuthResult {
  final bool success;
  final User? user;
  final String? error;

  AuthResult({
    required this.success,
    this.user,
    this.error,
  });
}
