import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

import '../config/app_config.dart';
import 'auth_state.dart';
import 'me_service.dart';

/// Result of a price calculation from /mobile/v1/subscription/calc.
class CalcResult {
  const CalcResult({required this.priceKopeks, required this.priceRub});

  final int priceKopeks;
  final double priceRub;
}

/// Balance data returned from GET /mobile/v1/balance.
class BalanceData {
  const BalanceData({
    required this.balanceKopeks,
    required this.balanceRub,
    required this.autopayEnabled,
    required this.autopayDaysBefore,
  });

  final int balanceKopeks;
  final double balanceRub;
  final bool autopayEnabled;
  final int autopayDaysBefore;
}

/// Service for all subscription purchase and management API calls.
///
/// All methods pass [X-Telegram-Id] from [authStateNotifier].
/// After a successful purchase, callers should call [MeService.refresh].
class SubscriptionApiService {
  SubscriptionApiService._();

  static String get _base => AppConfig.backendBaseUrl;

  static Map<String, String> _headers() {
    final auth = authStateNotifier.value;
    return {
      'Content-Type': 'application/json',
      if (auth.telegramId != null) 'X-Telegram-Id': auth.telegramId.toString(),
    };
  }

  // ── Price calculation ───────────────────────────────────────────────────

  /// Request the calculated price for the given configuration.
  ///
  /// Returns null on network error or server error.
  static Future<CalcResult?> calcPrice({
    required int days,
    required int trafficGb,
    required int devices,
  }) async {
    try {
      final resp = await http
          .post(
            Uri.parse('$_base/mobile/v1/subscription/calc'),
            headers: _headers(),
            body: jsonEncode({
              'days': days,
              'traffic_gb': trafficGb,
              'devices': devices,
            }),
          )
          .timeout(const Duration(seconds: 15));

      if (resp.statusCode == 200) {
        final body = jsonDecode(resp.body) as Map<String, dynamic>;
        return CalcResult(
          priceKopeks: (body['price_kopeks'] as num).toInt(),
          priceRub: (body['price_rub'] as num).toDouble(),
        );
      }
      debugPrint('SubscriptionApiService: calc ${resp.statusCode}');
      return null;
    } on Exception catch (e) {
      debugPrint('SubscriptionApiService: calcPrice error: $e');
      return null;
    }
  }

  // ── Purchase ────────────────────────────────────────────────────────────

  /// Initiate a subscription purchase.
  ///
  /// Returns the payment URL string on success (open in browser),
  /// `'balance'` if paid directly from balance, or throws [Exception] on error.
  static Future<String?> buySubscription({
    required int days,
    required int trafficGb,
    required int devices,
    String paymentMethod = 'yookassa',
  }) async {
    final resp = await http
        .post(
          Uri.parse('$_base/mobile/v1/subscription/buy'),
          headers: _headers(),
          body: jsonEncode({
            'days': days,
            'traffic_gb': trafficGb,
            'devices': devices,
            'payment_method': paymentMethod,
          }),
        )
        .timeout(const Duration(seconds: 20));

    if (resp.statusCode == 200) {
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      if (body['paid_from_balance'] == true) return 'balance';
      return body['payment_url'] as String?;
    }
    if (resp.statusCode == 402) throw Exception('Недостаточно средств на балансе');
    if (resp.statusCode == 503) throw Exception('Оплата временно недоступна');
    throw Exception('Ошибка сервера (${resp.statusCode})');
  }

  // ── Upgrade ─────────────────────────────────────────────────────────────

  /// Upgrade the active subscription.
  ///
  /// [action]: `'traffic'` | `'devices'` | `'days'`
  ///
  /// Returns the payment URL or `'balance'`, throws on error.
  static Future<String?> upgradeSubscription({
    required String action,
    required int value,
    String paymentMethod = 'yookassa',
  }) async {
    final resp = await http
        .post(
          Uri.parse('$_base/mobile/v1/subscription/upgrade'),
          headers: _headers(),
          body: jsonEncode({
            'action': action,
            'value': value,
            'payment_method': paymentMethod,
          }),
        )
        .timeout(const Duration(seconds: 20));

    if (resp.statusCode == 200) {
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      if (body['paid_from_balance'] == true) return 'balance';
      return body['payment_url'] as String?;
    }
    if (resp.statusCode == 402) throw Exception('Недостаточно средств на балансе');
    throw Exception('Ошибка сервера (${resp.statusCode})');
  }

  // ── Balance ─────────────────────────────────────────────────────────────

  static Future<BalanceData?> fetchBalance() async {
    try {
      final resp = await http
          .get(Uri.parse('$_base/mobile/v1/balance'), headers: _headers())
          .timeout(const Duration(seconds: 15));

      if (resp.statusCode == 200) {
        final body = jsonDecode(resp.body) as Map<String, dynamic>;
        return BalanceData(
          balanceKopeks: (body['balance_kopeks'] as num).toInt(),
          balanceRub: (body['balance_rub'] as num).toDouble(),
          autopayEnabled: body['autopay_enabled'] as bool? ?? false,
          autopayDaysBefore: (body['autopay_days_before'] as num?)?.toInt() ?? 3,
        );
      }
      debugPrint('SubscriptionApiService: balance ${resp.statusCode}');
      return null;
    } on Exception catch (e) {
      debugPrint('SubscriptionApiService: fetchBalance error: $e');
      return null;
    }
  }

  // ── Autopay ─────────────────────────────────────────────────────────────

  /// Toggle auto-renewal.  Returns the server-confirmed state, or null on error.
  static Future<bool?> setAutopay(bool enabled) async {
    try {
      final resp = await http
          .put(
            Uri.parse('$_base/mobile/v1/subscription/autopay'),
            headers: _headers(),
            body: jsonEncode({'enabled': enabled}),
          )
          .timeout(const Duration(seconds: 15));

      if (resp.statusCode == 200) {
        final body = jsonDecode(resp.body) as Map<String, dynamic>;
        return body['enabled'] as bool?;
      }
      return null;
    } on Exception catch (e) {
      debugPrint('SubscriptionApiService: setAutopay error: $e');
      return null;
    }
  }

  // ── URL helper ──────────────────────────────────────────────────────────

  /// Open [url] in the external browser.
  static Future<void> openPaymentUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else {
      debugPrint('SubscriptionApiService: cannot launch $url');
    }
  }
}
