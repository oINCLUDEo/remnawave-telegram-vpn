import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../config/app_config.dart';
import 'auth_state.dart';

// ─────────────────────────────────────────────────────────────────────────────
// Models
// ─────────────────────────────────────────────────────────────────────────────

class ReferralInfo {
  const ReferralInfo({
    required this.referralCode,
    required this.referralLink,
    required this.totalReferrals,
    required this.totalEarningsKopeks,
    required this.totalEarningsRubles,
    required this.commissionPercent,
    required this.programEnabled,
  });

  final String referralCode;
  final String referralLink;
  final int totalReferrals;
  final int totalEarningsKopeks;
  final double totalEarningsRubles;
  final int commissionPercent;
  final bool programEnabled;

  factory ReferralInfo.fromJson(Map<String, dynamic> json) {
    return ReferralInfo(
      referralCode: json['referral_code'] as String? ?? '',
      referralLink: json['referral_link'] as String? ?? '',
      totalReferrals: (json['total_referrals'] as num?)?.toInt() ?? 0,
      totalEarningsKopeks: (json['total_earnings_kopeks'] as num?)?.toInt() ?? 0,
      totalEarningsRubles: (json['total_earnings_rubles'] as num?)?.toDouble() ?? 0.0,
      commissionPercent: (json['commission_percent'] as num?)?.toInt() ?? 0,
      programEnabled: json['program_enabled'] as bool? ?? true,
    );
  }
}

class PromoActivateResult {
  const PromoActivateResult({
    required this.success,
    required this.message,
    this.balanceBeforeRub = 0.0,
    this.balanceAfterRub = 0.0,
    this.bonusDescription,
  });

  final bool success;
  final String message;
  final double balanceBeforeRub;
  final double balanceAfterRub;
  final String? bonusDescription;

  factory PromoActivateResult.fromJson(Map<String, dynamic> json) {
    return PromoActivateResult(
      success: json['success'] as bool? ?? false,
      message: json['message'] as String? ?? '',
      balanceBeforeRub: (json['balance_before_rub'] as num?)?.toDouble() ?? 0.0,
      balanceAfterRub: (json['balance_after_rub'] as num?)?.toDouble() ?? 0.0,
      bonusDescription: json['bonus_description'] as String?,
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Service
// ─────────────────────────────────────────────────────────────────────────────

class ReferralApiService {
  static String get _baseUrl => AppConfig.backendBaseUrl;

  static Map<String, String> get _headers {
    final id = authStateNotifier.value.telegramId;
    return {
      'Content-Type': 'application/json',
      if (id != null) 'X-Telegram-Id': id.toString(),
    };
  }

  /// Fetch referral info from GET /mobile/v1/referral.
  static Future<ReferralInfo?> getReferralInfo() async {
    try {
      final resp = await http
          .get(Uri.parse('$_baseUrl/mobile/v1/referral'), headers: _headers)
          .timeout(const Duration(seconds: 15));
      if (resp.statusCode == 200) {
        return ReferralInfo.fromJson(jsonDecode(resp.body) as Map<String, dynamic>);
      }
      debugPrint('ReferralApiService: GET /referral → ${resp.statusCode}');
      return null;
    } on Exception catch (e) {
      debugPrint('ReferralApiService: error $e');
      return null;
    }
  }

  /// Activate a promo code via POST /mobile/v1/promocode/activate.
  static Future<PromoActivateResult?> activatePromoCode(String code) async {
    try {
      final resp = await http
          .post(
            Uri.parse('$_baseUrl/mobile/v1/promocode/activate'),
            headers: _headers,
            body: jsonEncode({'code': code}),
          )
          .timeout(const Duration(seconds: 15));
      if (resp.statusCode == 200) {
        return PromoActivateResult.fromJson(jsonDecode(resp.body) as Map<String, dynamic>);
      }
      debugPrint('ReferralApiService: POST /promocode/activate → ${resp.statusCode}');
      // Try to parse error body
      try {
        final body = jsonDecode(resp.body) as Map<String, dynamic>;
        return PromoActivateResult(
          success: false,
          message: body['detail'] as String? ?? 'Ошибка сервера',
        );
      } catch (_) {}
      return const PromoActivateResult(success: false, message: 'Ошибка сервера');
    } on Exception catch (e) {
      debugPrint('ReferralApiService: activatePromoCode error $e');
      return const PromoActivateResult(success: false, message: 'Ошибка соединения');
    }
  }
}
