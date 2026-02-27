import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_v2ray/flutter_v2ray.dart';

import '../../../../core/network/api_client.dart';
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
  VpnCubit({required this.dataSource, required this.apiClient})
      : super(const VpnState()) {
    _v2ray = FlutterV2ray(
      onStatusChanged: _onV2RayStatusChanged,
    );
  }

  final VpnRemoteDataSource dataSource;
  final ApiClient apiClient;
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
  ///
  /// [preferredMatchKey] is an optional hint (typically a config profile
  /// name) used to select the most appropriate config from the subscription
  /// for the server chosen in the UI. When null, the first valid config is
  /// used as before.
  Future<void> connect({String? preferredMatchKey}) async {
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

      // Resolve subscription URL:
      // - absolute URLs (with scheme) are fetched directly;
      // - relative URLs are fetched via [ApiClient] so the JWT token
      //   is attached automatically.
      final uri = Uri.tryParse(subscriptionUrl);
      if (uri == null) {
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.error,
          error: () => 'Некорректный адрес подписки VPN',
        ));
        return;
      }

      final bool isAbsolute = uri.hasScheme;
      final dio = isAbsolute ? Dio() : apiClient.dio;
      final targetUrl = isAbsolute ? subscriptionUrl : subscriptionUrl;

      // Fetch the Remnawave subscription content.
      // The response body is base64-encoded text — one proxy link per line
      // (vmess://, vless://, trojan://, etc.)
      final response = await dio.get<String>(
        targetUrl,
        options: Options(responseType: ResponseType.plain),
      );
      final body = (response.data ?? '').trim();

      // Treat the body as a (potentially base64-encoded) list of subscription
      // links (vmess://, vless://, trojan://, etc.) and select the best match
      // for the chosen server, then build a full configuration via
      // [V2RayURL.getFullConfiguration] exactly as in the flutter_v2ray
      // reference example.

      // Decode base64 → UTF-8 text; fall back to plain text if not base64.
      // RemnaWave uses URL-safe base64 (RFC 4648 §5: `-` and `_` instead of
      // `+` and `/`), so we try base64Url first, then standard base64.
      String plainText;
      try {
        // Normalize missing padding before decoding
        final padded = _normalizePadding(body);
        plainText = utf8.decode(base64Url.decode(padded));
      } catch (_) {
        try {
          plainText = utf8.decode(base64.decode(_normalizePadding(body)));
        } catch (_) {
          plainText = body; // already plain-text proxy links
        }
      }

      // Split into individual proxy links
      final lines = plainText
          .split('\n')
          .map((l) => l.trim().replaceAll('\r', ''))
          .where((l) => l.isNotEmpty)
          .toList();

      if (lines.isEmpty) {
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.error,
          error: () => 'Сервер вернул пустую VPN-конфигурацию. '
              'Проверьте, что подписка активна и RemnaWave возвращает конфигурацию.',
        ));
        return;
      }

      // Parse all valid links into V2RayURL descriptors.
      final parsedConfigs = <V2RayURL>[];
      for (final link in lines) {
        try {
          parsedConfigs.add(FlutterV2ray.parseFromURL(link));
        } catch (_) {
          continue;
        }
      }

      if (parsedConfigs.isEmpty) {
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.error,
          error: () =>
              'Не удалось разобрать ни одну ссылку VPN. Формат ссылок не поддерживается или повреждён.',
        ));
        return;
      }

      // Choose the config whose remark matches the selected server,
      // falling back to the first one.
      V2RayURL selected = parsedConfigs.first;
      final key = (preferredMatchKey ?? '').toLowerCase();
      if (key.isNotEmpty) {
        for (final cfg in parsedConfigs) {
          final remark = (cfg.remark ?? '').toLowerCase();
          if (remark.contains(key)) {
            selected = cfg;
            break;
          }
        }
      }

      // Optionally, we could tweak inbound/dns/log here, similar to the
      // flutter_v2ray reference, but for now we use the config exactly as
      // generated by [getFullConfiguration].

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
        break;
      case 'CONNECTING':
        newStatus = VpnConnectionStatus.connecting;
        break;
      case 'DISCONNECTING':
        newStatus = VpnConnectionStatus.disconnecting;
        break;
      case 'DISCONNECTED':
        newStatus = VpnConnectionStatus.disconnected;
        break;
      case 'ERROR':
        newStatus = VpnConnectionStatus.error;
        break;
      default:
        newStatus = state.connectionStatus;
    }

    emit(state.copyWith(
      connectionStatus: newStatus,
      downloadSpeed: status.download.toString(),
      uploadSpeed: status.upload.toString(),
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
