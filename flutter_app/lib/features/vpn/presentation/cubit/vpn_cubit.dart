import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_v2ray/flutter_v2ray.dart';

import '../../data/datasources/vpn_remote_datasource.dart';
import 'vpn_state.dart';

/// Manages VPN connection state and profile loading.
///
/// Connection flow:
///   1. [loadProfile] — fetches GET /mobile/v1/profile with JWT.
///      On 401 the profile stays null (no subscription yet).
///   2. [connect] — fetches the Remnawave subscription URL, parses the
///      proxy configs via [FlutterV2ray.parseUrl], selects the best config
///      and starts the in-app VPN tunnel via [FlutterV2ray.startV2Ray].
///   3. Status updates arrive via [FlutterV2ray]'s [onStatusChanged] callback
///      and are forwarded to the Cubit state.
///   4. [disconnect] — stops the tunnel via [FlutterV2ray.stopV2Ray].
class VpnCubit extends Cubit<VpnState> {
  VpnCubit({required this.dataSource}) : super(const VpnState()) {
    _v2ray = FlutterV2ray(
      onStatusChanged: _onV2RayStatusChanged,
    );
  }

  final VpnRemoteDataSource dataSource;
  late final FlutterV2ray _v2ray;
  bool _v2rayInitialized = false;

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  Future<void> _ensureInitialized() async {
    if (_v2rayInitialized) return;
    await _v2ray.initializeV2Ray(
      notificationIconResourceType: 'drawable',
      notificationIconResourceName: 'ic_launcher',
    );
    _v2rayInitialized = true;
  }

  // ── Profile ───────────────────────────────────────────────────────────────

  /// Loads the user's VPN profile from the backend.
  /// Silent 401 → stays disconnected with null profile (no subscription).
  Future<void> loadProfile() async {
    emit(state.copyWith(isLoadingProfile: true, error: () => null));
    try {
      final profile = await dataSource.getProfile();
      emit(state.copyWith(
        profile: profile,
        isLoadingProfile: false,
      ));
    } on DioException catch (e) {
      final isAuthError =
          e.response?.statusCode == 401 || e.response?.statusCode == 403;
      emit(state.copyWith(
        isLoadingProfile: false,
        error: () => isAuthError ? null : _friendlyDioError(e),
      ));
    } catch (_) {
      emit(state.copyWith(
        isLoadingProfile: false,
        error: () => 'Не удалось загрузить профиль',
      ));
    }
  }

  // ── Connection ────────────────────────────────────────────────────────────

  /// Starts the in-app VPN tunnel using the Remnawave subscription URL.
  Future<void> connect() async {
    final subscriptionUrl = state.profile?.subscriptionUrl;
    if (subscriptionUrl == null || subscriptionUrl.isEmpty) {
      emit(state.copyWith(error: () => 'Нет активной подписки'));
      return;
    }

    emit(state.copyWith(
      connectionStatus: VpnConnectionStatus.connecting,
      error: () => null,
    ));

    try {
      await _ensureInitialized();

      // Request VPN permission (Android only; no-op on iOS)
      if (!await _v2ray.requestPermission()) {
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.error,
          error: () => 'Разрешение на VPN не предоставлено',
        ));
        return;
      }

      // Fetch the Remnawave subscription URL.
      // The response body is base64-encoded text — one proxy link per line
      // (vmess://, vless://, trojan://, etc.)
      final response = await Dio().get<String>(
        subscriptionUrl,
        options: Options(responseType: ResponseType.plain),
      );
      final body = (response.data ?? '').trim();

      // Decode base64 → UTF-8 text; fall back to plain text if not base64.
      // RemnaWave uses MIME base64 (line breaks every 76 chars) or URL-safe
      // base64.  Strip ALL whitespace before padding normalisation so that
      // embedded `\n` / `\r` don't cause decode failures.
      String plainText;
      final compactBody = body.replaceAll(RegExp(r'\s'), '');
      try {
        // URL-safe base64 first (RFC 4648 §5: `-` and `_`)
        plainText = utf8.decode(base64Url.decode(_normalizePadding(compactBody)));
      } catch (_) {
        try {
          // Standard base64 fallback (`+` and `/`)
          plainText = utf8.decode(base64.decode(_normalizePadding(compactBody)));
        } catch (_) {
          plainText = body; // already plain-text proxy links
        }
      }

      // Split into individual proxy links.
      // Only lines that start with a known VPN scheme are candidate configs.
      const _knownSchemes = [
        'vless://', 'vmess://', 'trojan://', 'ss://',
        'hysteria2://', 'tuic://',
      ];
      final lines = plainText
          .split('\n')
          .map((l) => l.trim().replaceAll('\r', ''))
          .where((l) => l.isNotEmpty)
          .toList();
      final candidateLinks = lines
          .where((l) => _knownSchemes.any(l.startsWith))
          .toList();

      V2RayURL? selected;
      for (final link in candidateLinks) {
        try {
          final parsed = FlutterV2ray.parseFromURL(link);
          if (parsed.configType != 'ERROR') {
            selected = parsed;
            break; // use first valid config
          }
        } catch (_) {
          continue;
        }
      }

      if (selected == null) {
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.error,
          error: () =>
              'Не удалось разобрать конфигурацию VPN '
              '(всего строк: ${lines.length}, '
              'VPN-ссылок: ${candidateLinks.length})',
        ));
        return;
      }

      await _v2ray.startV2Ray(
        remark: selected.remark,
        config: selected.getFullConfiguration(),
        blockedApps: null,
        bypassSubnets: null,
        proxyOnly: false,
      );

      emit(state.copyWith(
        activeConfigRemark: selected.remark,
      ));
    } catch (e) {
      emit(state.copyWith(
        connectionStatus: VpnConnectionStatus.error,
        error: () => 'Ошибка подключения: $e',
      ));
    }
  }

  /// Stops the in-app VPN tunnel.
  Future<void> disconnect() async {
    emit(state.copyWith(
      connectionStatus: VpnConnectionStatus.disconnecting,
      error: () => null,
    ));
    try {
      await _v2ray.stopV2Ray();
      // Definitive state is set by _onV2RayStatusChanged;
      // emit disconnected immediately as fallback
      emit(state.copyWith(
        connectionStatus: VpnConnectionStatus.disconnected,
        downloadSpeed: '',
        uploadSpeed: '',
        connectionDuration: '',
        activeConfigRemark: null,
      ));
    } catch (e) {
      emit(state.copyWith(
        connectionStatus: VpnConnectionStatus.disconnected,
        error: () => 'Ошибка при отключении: $e',
      ));
    }
  }

  // ── V2Ray status callback ─────────────────────────────────────────────────

  void _onV2RayStatusChanged(V2RayStatus status) {
    final stateStr = status.state.toUpperCase();
    VpnConnectionStatus newStatus;

    switch (stateStr) {
      case 'CONNECTED':
        newStatus = VpnConnectionStatus.connected;
      case 'CONNECTING':
        newStatus = VpnConnectionStatus.connecting;
      case 'DISCONNECTING':
        newStatus = VpnConnectionStatus.disconnecting;
      case 'DISCONNECTED':
        newStatus = VpnConnectionStatus.disconnected;
      case 'ERROR':
        newStatus = VpnConnectionStatus.error;
      default:
        newStatus = state.connectionStatus;
    }

    emit(state.copyWith(
      connectionStatus: newStatus,
      downloadSpeed: status.download,
      uploadSpeed: status.upload,
      connectionDuration: status.duration,
      error: stateStr == 'ERROR' ? () => 'Ошибка VPN соединения' : null,
    ));
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  /// Adds `=` padding so base64/base64Url decoders don't throw.
  static String _normalizePadding(String s) {
    final rem = s.length % 4;
    if (rem == 0) return s;
    return s + '=' * (4 - rem);
  }

  String _friendlyDioError(DioException e) {
    if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      return 'Нет соединения с сервером';
    }
    if (e.type == DioExceptionType.connectionError) {
      return 'Проверьте подключение к интернету';
    }
    return 'Ошибка загрузки профиля';
  }
}
