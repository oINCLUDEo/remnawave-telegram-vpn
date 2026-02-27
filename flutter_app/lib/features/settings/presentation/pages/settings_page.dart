import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/di/injection.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/storage/secure_storage_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../vpn/presentation/cubit/vpn_cubit.dart';
import '../../../vpn/presentation/cubit/vpn_state.dart';
import '../../../vpn/presentation/widgets/glass_card.dart';

/// App settings screen.
///
/// Accessible via the gear icon in [VpnHomePage]'s AppBar.
/// Receives the active [VpnCubit] via [BlocProvider.value] so that
/// [_fetchDevToken] can reload the profile without re-creating the cubit.
class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

// Hardcoded test vless link — used to verify flutter_v2ray works independently
// of subscription fetching. Replace with any working vless/vmess/trojan link.
const _kTestLink =
    'vless://8a3f9a02-8202-4100-8083-b3b9b3e325c2@ee01-server.ulya.space:443'
    '?security=reality&type=tcp&headerType=&path=&host='
    '&flow=xtls-rprx-vision&sni=cloudflare.com&fp='
    '&pbk=b8SpqC5IqVGD5D1TatWNDrtykWvwHWKLoDAOdU2hXks'
    '&sid=#%F0%9F%87%AA%F0%9F%87%AA%20%D0%AD%D1%81%D1%82%D0%BE%D0%BD%D0%B8%D1%8F%20%231';

class _SettingsPageState extends State<SettingsPage> {
  bool _isLoading = false;
  String? _message;
  bool _isSuccess = false;

  // Test-connection card state
  late final TextEditingController _linkController;

  @override
  void initState() {
    super.initState();
    _linkController = TextEditingController(text: _kTestLink);
  }

  @override
  void dispose() {
    _linkController.dispose();
    super.dispose();
  }

  Future<void> _fetchDevToken() async {
    setState(() {
      _isLoading = true;
      _message = null;
    });

    try {
      // Use the same base URL that ApiClient uses.
      final baseUrl = sl<ApiClient>().dio.options.baseUrl;
      // Trailing slash guard
      final cleanBase = baseUrl.endsWith('/')
          ? baseUrl.substring(0, baseUrl.length - 1)
          : baseUrl;
      final url = '$cleanBase/mobile/v1/dev/auth';

      final dio = Dio(BaseOptions(
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ));
      final response = await dio.post<Map<String, dynamic>>(url);

      final token = response.data?['access_token'] as String?;
      if (token == null || token.isEmpty) {
        throw Exception('Сервер не вернул токен');
      }

      await sl<SecureStorageService>().saveAccessTokenOnly(token);

      // Reload the VPN profile with the new token.
      if (mounted) {
        context.read<VpnCubit>().loadProfile();
      }

      final username = response.data?['username'] ?? 'неизвестно';
      setState(() {
        _isSuccess = true;
        _message = 'Токен получен для @$username. Профиль обновляется…';
      });
    } on DioException catch (e) {
      final code = e.response?.statusCode;
      String msg;
      if (code == 404) {
        msg = 'DEV_MODE не включён на сервере (404). '
            'Добавьте DEV_MODE=true и DEV_USER_TELEGRAM_ID в .env и перезапустите бот.';
      } else if (code == 500) {
        final detail = e.response?.data?['detail'] ?? '';
        msg = 'Ошибка сервера: $detail';
      } else {
        msg = 'Ошибка сети: ${e.message}';
      }
      setState(() {
        _isSuccess = false;
        _message = msg;
      });
    } catch (e) {
      setState(() {
        _isSuccess = false;
        _message = 'Ошибка: $e';
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final baseUrl = sl<ApiClient>().dio.options.baseUrl;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppColors.background, AppColors.backgroundDark],
          ),
        ),
        child: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              // ── Header ──────────────────────────────────────────────────
              Padding(
                padding: const EdgeInsets.only(top: 8, bottom: 24),
                child: Row(
                  children: [
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.arrow_back_ios_new_rounded,
                          color: AppColors.textPrimary, size: 18),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                    const SizedBox(width: 12),
                    const Text(
                      'Настройки',
                      style: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),

              // ── API section ──────────────────────────────────────────────
              const _SectionHeader(label: 'Соединение'),
              const SizedBox(height: 8),
              GlassCard(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                child: Row(
                  children: [
                    const Icon(Icons.dns_rounded,
                        color: AppColors.accent, size: 18),
                    const SizedBox(width: 10),
                    const Text('Сервер API',
                        style: TextStyle(
                            color: AppColors.textSecondary, fontSize: 13)),
                    const Spacer(),
                    Flexible(
                      child: Text(
                        baseUrl,
                        textAlign: TextAlign.end,
                        style: const TextStyle(
                            color: AppColors.textPrimary,
                            fontSize: 12,
                            fontFamily: 'monospace'),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              // ── Developer section ────────────────────────────────────────
              const _SectionHeader(label: 'Разработка'),
              const SizedBox(height: 8),
              GlassCard(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Тестовый токен',
                      style: TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 15,
                          fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Получить JWT для тестового аккаунта без пароля.\n'
                      'Требует DEV_MODE=true и DEV_USER_TELEGRAM_ID на сервере.',
                      style: TextStyle(
                          color: AppColors.textSecondary, fontSize: 12),
                    ),
                    const SizedBox(height: 14),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: _isLoading ? null : _fetchDevToken,
                        icon: _isLoading
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.black87),
                              )
                            : const Icon(Icons.vpn_key_rounded,
                                size: 18, color: Colors.black87),
                        label: Text(
                          _isLoading
                              ? 'Запрос...'
                              : 'Получить тестовый токен',
                          style: const TextStyle(
                              color: Colors.black87,
                              fontWeight: FontWeight.w600),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.accent,
                          disabledBackgroundColor:
                              AppColors.accent.withValues(alpha: 0.5),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12)),
                        ),
                      ),
                    ),
                    if (_message != null) ...[
                      const SizedBox(height: 12),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: (_isSuccess
                                  ? AppColors.signal
                                  : Colors.redAccent)
                              .withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: (_isSuccess
                                    ? AppColors.signal
                                    : Colors.redAccent)
                                .withValues(alpha: 0.4),
                          ),
                        ),
                        child: Text(
                          _message!,
                          style: TextStyle(
                            color: _isSuccess
                                ? AppColors.signal
                                : Colors.redAccent,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),

              const SizedBox(height: 24),

              // ── Test VPN connection ───────────────────────────────────────
              const _SectionHeader(label: 'Тест VPN'),
              const SizedBox(height: 8),
              GlassCard(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Прямое подключение',
                      style: TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 15,
                          fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Проверить что flutter_v2ray работает, минуя получение подписки. '
                      'Вставьте vless:// или vmess:// ссылку и нажмите Подключить.',
                      style: TextStyle(
                          color: AppColors.textSecondary, fontSize: 12),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _linkController,
                      style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 12,
                          fontFamily: 'monospace'),
                      maxLines: 3,
                      decoration: InputDecoration(
                        filled: true,
                        fillColor:
                            AppColors.backgroundDark.withValues(alpha: 0.5),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide(
                              color: Colors.white.withValues(alpha: 0.1)),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide(
                              color: Colors.white.withValues(alpha: 0.1)),
                        ),
                        hintText: 'vless://...',
                        hintStyle: const TextStyle(
                            color: AppColors.textSecondary, fontSize: 12),
                        contentPadding: const EdgeInsets.all(10),
                      ),
                    ),
                    const SizedBox(height: 12),
                    BlocBuilder<VpnCubit, VpnState>(
                      builder: (context, vpnState) {
                        final isConnecting = vpnState.connectionStatus ==
                            VpnConnectionStatus.connecting;
                        final isConnected = vpnState.connectionStatus ==
                            VpnConnectionStatus.connected;
                        return Row(
                          children: [
                            Expanded(
                              child: ElevatedButton(
                                onPressed: isConnecting
                                    ? null
                                    : () => isConnected
                                        ? context.read<VpnCubit>().disconnect()
                                        : context
                                            .read<VpnCubit>()
                                            .connectDirect(
                                                _linkController.text),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: isConnected
                                      ? Colors.redAccent
                                      : AppColors.signal,
                                  disabledBackgroundColor:
                                      AppColors.signal.withValues(alpha: 0.4),
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 12),
                                  shape: RoundedRectangleBorder(
                                      borderRadius:
                                          BorderRadius.circular(12)),
                                ),
                                child: Text(
                                  isConnecting
                                      ? 'Подключение…'
                                      : isConnected
                                          ? 'Отключить'
                                          : 'Подключить напрямую',
                                  style: const TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w600,
                                      fontSize: 13),
                                ),
                              ),
                            ),
                            if (vpnState.connectionStatus ==
                                VpnConnectionStatus.connected) ...[
                              const SizedBox(width: 10),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 10, vertical: 6),
                                decoration: BoxDecoration(
                                  color: AppColors.signal
                                      .withValues(alpha: 0.15),
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(
                                      color: AppColors.signal
                                          .withValues(alpha: 0.4)),
                                ),
                                child: Text(
                                  vpnState.activeConfigRemark ?? 'Подключено',
                                  style: const TextStyle(
                                      color: AppColors.signal,
                                      fontSize: 11),
                                ),
                              ),
                            ],
                          ],
                        );
                      },
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              // ── Instructions ─────────────────────────────────────────────
              GlassCard(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.info_outline_rounded,
                            color: AppColors.accent, size: 16),
                        SizedBox(width: 8),
                        Text(
                          'Как настроить dev-режим',
                          style: TextStyle(
                              color: AppColors.textPrimary,
                              fontSize: 14,
                              fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    ..._instructions.map((step) => Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: Text(
                            step,
                            style: const TextStyle(
                                color: AppColors.textSecondary,
                                fontSize: 12,
                                height: 1.5),
                          ),
                        )),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

const _instructions = [
  '1. Добавьте в .env:\n   DEV_MODE=true\n   DEV_USER_TELEGRAM_ID=<ваш_telegram_id>',
  '2. Перезапустите бот:\n   docker compose down && docker compose up -d',
  '3. Нажмите «Получить тестовый токен» — токен сохранится автоматически.',
  '4. Вернитесь на главный экран и нажмите «Подключиться».',
];

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 4),
      child: Text(
        label.toUpperCase(),
        style: const TextStyle(
          color: AppColors.textSecondary,
          fontSize: 11,
          fontWeight: FontWeight.w600,
          letterSpacing: 1.2,
        ),
      ),
    );
  }
}
