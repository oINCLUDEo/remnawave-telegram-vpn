import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../config/app_config.dart';
import 'auth_state.dart';
import 'remnawave_service.dart';

/// Service that calls the mobile auth backend endpoints and updates
/// [authStateNotifier] on success.
class AuthService {
  AuthService._();

  // ── API endpoint ──────────────────────────────────────────────────────────

  static String get _authEndpoint =>
      '${AppConfig.backendBaseUrl}/mobile/v1/auth/telegram/widget';

  // ── Login ─────────────────────────────────────────────────────────────────

  /// Authenticate with Telegram Login Widget data received from the WebView.
  ///
  /// Returns `null` on success (state is updated via [authStateNotifier]).
  /// Returns a localised error message string on failure.
  static Future<String?> loginWithWidgetData(
    Map<String, dynamic> widgetData,
  ) async {
    try {
      final response = await http
          .post(
            Uri.parse(_authEndpoint),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(widgetData),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        return await _applyAuthResponse(body);
      }

      if (response.statusCode == 401) {
        return 'Данные авторизации Telegram недействительны или устарели.';
      }
      if (response.statusCode == 403) {
        return 'Учётная запись заблокирована.';
      }
      if (response.statusCode == 503) {
        return 'Авторизация через Telegram временно недоступна.';
      }

      return 'Ошибка сервера (${response.statusCode}). Попробуйте позже.';
    } on Exception catch (e) {
      return 'Не удалось подключиться к серверу: $e';
    }
  }

  /// Apply a successful auth response: persist auth state and subscription URL.
  ///
  /// Returns `null` on success, or an error string if the response is malformed.
  static Future<String?> _applyAuthResponse(Map<String, dynamic> body) async {
    try {
      final userMap = body['user'] as Map<String, dynamic>?;
      if (userMap == null) return 'Неверный формат ответа сервера.';

      final newState = AuthState(
        isLoggedIn: true,
        telegramId: userMap['telegram_id'] as int?,
        firstName: userMap['first_name'] as String?,
        lastName: userMap['last_name'] as String?,
        username: userMap['username'] as String?,
        subscriptionUrl: body['subscription_url'] as String?,
      );

      // Persist auth state (user info only — not the subscription URL).
      await saveAuthState(newState);

      // If the backend returned a subscription URL, store it so that
      // RemnawaveService.getSubscriptionUrl() picks it up on the next load.
      final subUrl = body['subscription_url'] as String?;
      if (subUrl != null && subUrl.isNotEmpty) {
        await RemnawaveService.saveSubscriptionUrl(subUrl);
      }

      // Broadcast the new state globally.
      authStateNotifier.value = newState;
      return null; // success
    } on Exception catch (e) {
      return 'Ошибка разбора ответа: $e';
    }
  }

  // ── Logout ────────────────────────────────────────────────────────────────

  /// Clear the authenticated session and subscription URL.
  static Future<void> logout() async {
    await clearAuthState();
    // Remove subscription URL so the app falls back to public catalog.
    await RemnawaveService.saveSubscriptionUrl('');
  }
}
