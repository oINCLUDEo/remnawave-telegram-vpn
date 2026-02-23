import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class StorageService {
  static late SharedPreferences _prefs;
  static const FlutterSecureStorage _secureStorage = FlutterSecureStorage();

  // Keys
  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';
  static const String _userIdKey = 'user_id';
  static const String _languageKey = 'language';

  static Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }

  // Token management
  static Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _secureStorage.write(key: _accessTokenKey, value: accessToken);
    await _secureStorage.write(key: _refreshTokenKey, value: refreshToken);
  }

  static Future<String?> getAccessToken() async {
    return await _secureStorage.read(key: _accessTokenKey);
  }

  static Future<String?> getRefreshToken() async {
    return await _secureStorage.read(key: _refreshTokenKey);
  }

  static Future<void> clearTokens() async {
    await _secureStorage.delete(key: _accessTokenKey);
    await _secureStorage.delete(key: _refreshTokenKey);
  }

  // User ID
  static Future<void> saveUserId(int userId) async {
    await _prefs.setInt(_userIdKey, userId);
  }

  static int? getUserId() {
    return _prefs.getInt(_userIdKey);
  }

  static Future<void> clearUserId() async {
    await _prefs.remove(_userIdKey);
  }

  // Language
  static Future<void> saveLanguage(String language) async {
    await _prefs.setString(_languageKey, language);
  }

  static String? getLanguage() {
    return _prefs.getString(_languageKey);
  }

  // Clear all data
  static Future<void> clearAll() async {
    await clearTokens();
    await clearUserId();
    await _prefs.clear();
  }
}
