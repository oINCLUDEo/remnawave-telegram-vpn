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
      notificationIconResourceType: 'mipmap',
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
  /// Connection flow:
  ///   1. Request Android VPN permission.
  ///   2. Try GET /mobile/v1/vpn-config (backend decodes base64 server-side).
  ///   3. If empty/fails, fetch [subscriptionUrl] directly from the device
  ///      and decode with [_parseSubscriptionBody].
  ///   4. Parse each proxy link with [FlutterV2ray.parseFromURL].
  ///   5. Prefer the config whose remark contains [preferredMatchKey].
  ///   6. Start V2Ray tunnel via [FlutterV2ray.startV2Ray].
  ///
  /// [preferredMatchKey] — optional hint (typically the server squad name)
  /// used to choose the best proxy from the subscription. Falls back to the
  /// first valid config when null or unmatched.
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

      // Request VPN permission (Android only; no-op on iOS).
      if (!await _v2ray.requestPermission()) {
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.disconnected,
          error: () => 'Разрешение на VPN не предоставлено',
        ));
        return;
      }

      // ── Strategy 1: backend proxy endpoint ──────────────────────────────
      // GET /mobile/v1/vpn-config — server fetches the subscription,
      // decodes base64 and returns clean proxy links. Most reliable because
      // it avoids mobile network quirks.
      List<String> candidateLinks = [];
      try {
        candidateLinks = await dataSource.getVpnConfig();
      } catch (_) {
        // Backend unavailable or no subscription → try direct fetch.
      }

      // ── Strategy 2: fetch subscription (relative → backend proxy, absolute → direct) ──
      // When subscription_url is a relative path (e.g. "/mobile/v1/profile/subscription")
      // the backend is acting as a proxy that adds HWID + JWT. Use apiClient.dio so it
      // inherits the base URL and Bearer token automatically.
      // When subscription_url is an absolute external URL (e.g. "https://sub.example.com/…")
      // use a plain Dio instance with User-Agent.
      if (candidateLinks.isEmpty) {
        final isRelative = subscriptionUrl.startsWith('/');
        Response<String> response;
        if (isRelative) {
          response = await apiClient.dio.get<String>(
            subscriptionUrl,
            options: Options(
              responseType: ResponseType.plain,
              sendTimeout: const Duration(seconds: 15),
              receiveTimeout: const Duration(seconds: 15),
            ),
          );
        } else {
          response = await Dio().get<String>(
            subscriptionUrl,
            options: Options(
              responseType: ResponseType.plain,
              headers: {'User-Agent': 'v2rayN/6.0'},
              sendTimeout: const Duration(seconds: 15),
              receiveTimeout: const Duration(seconds: 15),
            ),
          );
        }
        final body = (response.data ?? '').trim();
        candidateLinks = _parseSubscriptionBody(body);
      }

      if (candidateLinks.isEmpty) {
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.disconnected,
          error: () =>
              'Не удалось получить конфигурацию VPN. '
              'Убедитесь, что подписка активна и сервер доступен.',
        ));
        return;
      }

      // ── Parse proxy links into V2RayURL descriptors ───────────────────────
      final parsedConfigs = <V2RayURL>[];
      for (final link in candidateLinks) {
        try {
          parsedConfigs.add(FlutterV2ray.parseFromURL(link));
        } catch (_) {
          // Skip unsupported or malformed links.
        }
      }

      if (parsedConfigs.isEmpty) {
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.disconnected,
          error: () =>
              'Ни одна VPN-ссылка не поддерживается '
              '(${candidateLinks.length} ссылок получено)',
        ));
        return;
      }

      // ── Select the best matching config ───────────────────────────────────
      // Prefer a config whose remark contains the selected server name.
      // Falls back to the first config in the list.
      V2RayURL selected = parsedConfigs.first;
      final key = (preferredMatchKey ?? '').toLowerCase().trim();
      if (key.isNotEmpty) {
        for (final cfg in parsedConfigs) {
          final remark = cfg.remark.toLowerCase();
          if (remark.contains(key)) {
            selected = cfg;
            break;
          }
        }
      }

      // ── Build full V2Ray JSON and start the tunnel ─────────────────────────
      final rawConfig = selected.getFullConfiguration();
      if (rawConfig.isEmpty) {
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.disconnected,
          error: () =>
              'Не удалось сформировать конфигурацию для "${selected.remark}"',
        ));
        return;
      }
      final config = _patchConfig(rawConfig);

      await _v2ray.startV2Ray(
        remark: selected.remark,
        config: config,
        proxyOnly: false,
        bypassSubnets: [],
        notificationDisconnectButtonName: 'DISCONNECT',
      );

      // _onV2RayStatusChanged will fire CONNECTED when the tunnel is up.
      // Emit remark immediately so the UI shows the server name.
      emit(state.copyWith(activeConfigRemark: selected.remark));
    } catch (e) {
      emit(state.copyWith(
        connectionStatus: VpnConnectionStatus.disconnected,
        error: () => 'Ошибка подключения: $e',
      ));
    }
  }

  /// Connects with a raw pre-built V2Ray JSON config string, bypassing
  /// both subscription fetching AND URL parsing / [V2RayURL.getFullConfiguration].
  ///
  /// Use this when you have a known-good JSON config and want to verify
  /// that [FlutterV2ray.startV2Ray] and the Xray core itself work correctly.
  Future<void> connectWithRawConfig(String jsonConfig) async {
    if (jsonConfig.trim().isEmpty) {
      emit(state.copyWith(error: () => 'JSON конфиг не должен быть пустым'));
      return;
    }

    emit(state.copyWith(
      connectionStatus: VpnConnectionStatus.connecting,
      error: () => null,
    ));

    try {
      await _ensureInitialized();

      if (!await _v2ray.requestPermission()) {
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.disconnected,
          error: () => 'Разрешение на VPN не предоставлено',
        ));
        return;
      }

      // Patch even manually provided configs (empty fp, etc.)
      final config = _patchConfig(jsonConfig.trim());

      // Extract a remark from the outbound tag or address for display.
      String remark = 'raw-config';
      try {
        final dynamic decoded = jsonDecode(config);
        if (decoded is Map<String, dynamic>) {
          final outbounds = decoded['outbounds'] as List?;
          final first = outbounds?.firstWhere(
            (o) => o is Map && (o as Map)['tag'] == 'proxy',
            orElse: () => outbounds?.isNotEmpty == true ? outbounds!.first : null,
          );
          if (first is Map<String, dynamic>) {
            final vnext = (first['settings']?['vnext'] as List?)?.firstOrNull;
            if (vnext is Map<String, dynamic>) {
              remark = vnext['address']?.toString() ?? remark;
            }
          }
        }
      } catch (_) {}

      await _v2ray.startV2Ray(
        remark: remark,
        config: config,
        proxyOnly: false,
        bypassSubnets: [],
        notificationDisconnectButtonName: 'DISCONNECT',
      );

      emit(state.copyWith(activeConfigRemark: remark));
    } catch (e) {
      emit(state.copyWith(
        connectionStatus: VpnConnectionStatus.disconnected,
        error: () => 'Ошибка connectWithRawConfig: $e',
      ));
    }
  }

  /// Returns the V2Ray JSON config that would be generated from [proxyLink]
  /// (after [_patchConfig] is applied), without actually starting the tunnel.
  ///
  /// Returns an error string prefixed with "ERROR:" when parsing fails.
  String getConfigPreview(String proxyLink) {
    if (proxyLink.trim().isEmpty) return 'ERROR: пустая ссылка';
    try {
      final parsed = FlutterV2ray.parseFromURL(proxyLink.trim());
      final raw = parsed.getFullConfiguration();
      if (raw.isEmpty) return 'ERROR: getFullConfiguration() вернул пустую строку';
      final patched = _patchConfig(raw);
      // Pretty-print for readability
      try {
        final dynamic decoded = jsonDecode(patched);
        return const JsonEncoder.withIndent('  ').convert(decoded);
      } catch (_) {
        return patched;
      }
    } catch (e) {
      return 'ERROR: $e';
    }
  }

  /// Connects directly with a single pre-decoded proxy link, bypassing all
  /// subscription fetching and base64 decoding.
  ///
  /// Use this to verify that [FlutterV2ray] itself works before debugging
  /// subscription parsing issues.
  Future<void> connectDirect(String proxyLink) async {
    if (proxyLink.trim().isEmpty) {
      emit(state.copyWith(error: () => 'Ссылка не должна быть пустой'));
      return;
    }

    emit(state.copyWith(
      connectionStatus: VpnConnectionStatus.connecting,
      error: () => null,
    ));

    try {
      await _ensureInitialized();

      if (!await _v2ray.requestPermission()) {
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.disconnected,
          error: () => 'Разрешение на VPN не предоставлено',
        ));
        return;
      }

      final V2RayURL parsed;
      try {
        parsed = FlutterV2ray.parseFromURL(proxyLink.trim());
      } catch (e) {
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.disconnected,
          error: () => 'Не удалось разобрать ссылку: $e',
        ));
        return;
      }

      final rawConfig = parsed.getFullConfiguration();
      if (rawConfig.isEmpty) {
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.disconnected,
          error: () => 'getFullConfiguration() вернул пустую строку для "${parsed.remark}"',
        ));
        return;
      }
      final config = _patchConfig(rawConfig);

      await _v2ray.startV2Ray(
        remark: parsed.remark,
        config: config,
        proxyOnly: false,
        bypassSubnets: [],
        notificationDisconnectButtonName: 'DISCONNECT',
      );

      emit(state.copyWith(activeConfigRemark: parsed.remark));
    } catch (e) {
      emit(state.copyWith(
        connectionStatus: VpnConnectionStatus.disconnected,
        error: () => 'Ошибка connectDirect: $e',
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
      downloadSpeed: status.downloadSpeed.toString(),
      uploadSpeed: status.uploadSpeed.toString(),
      connectionDuration: status.duration,
      error: stateStr == 'ERROR' ? () => 'Ошибка VPN соединения' : null,
    ));
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  static const _knownSchemes = [
    'vless://', 'vmess://', 'trojan://', 'ss://',
    'hysteria2://', 'tuic://', 'hysteria://',
  ];

  /// Decode a raw subscription response body into a list of proxy link strings.
  ///
  /// Handles MIME base64 (line-wrapped every 76 chars), URL-safe base64
  /// (RFC 4648 §5), and plain-text proxy link lists.
  static List<String> _parseSubscriptionBody(String body) {
    // Strip ALL whitespace so MIME \n line-wrapping doesn't break decoders.
    final compact = body.replaceAll(RegExp(r'\s'), '');

    String? plainText;
    for (final tryDecode in [base64Url.decode, base64.decode]) {
      try {
        final bytes = tryDecode(_normalizePadding(compact));
        final decoded = utf8.decode(bytes);
        // Only accept the decoded result if it contains at least one link
        if (_knownSchemes.any(decoded.contains)) {
          plainText = decoded;
          break;
        }
      } catch (_) {
        continue;
      }
    }
    plainText ??= body; // already plain-text proxy links

    return plainText
        .split('\n')
        .map((l) => l.trim().replaceAll('\r', ''))
        .where((l) => _knownSchemes.any(l.startsWith))
        .toList();
  }

  /// Adds `=` padding so base64/base64Url decoders don't throw.
  static String _normalizePadding(String s) {
    final rem = s.length % 4;
    if (rem == 0) return s;
    return s + '=' * (4 - rem);
  }

  /// Patches the V2Ray JSON config generated by [V2RayURL.getFullConfiguration].
  ///
  /// Fixes known issues:
  /// - Empty `fingerprint` for REALITY security → defaults to `"chrome"`.
  ///   Without a uTLS fingerprint, the REALITY handshake silently fails:
  ///   the TUN tunnel is up but the Xray proxy can't complete the outer TLS
  ///   negotiation, so packets are dropped and Android shows "connected" with
  ///   0 bytes transferred.
  static String _patchConfig(String config) {
    try {
      final dynamic decoded = jsonDecode(config);
      if (decoded is! Map<String, dynamic>) return config;

      bool modified = false;
      final outbounds = decoded['outbounds'];
      if (outbounds is List) {
        for (final outbound in outbounds) {
          if (outbound is! Map<String, dynamic>) continue;
          final stream = outbound['streamSettings'];
          if (stream is! Map<String, dynamic>) continue;
          if (stream['security'] != 'reality') continue;

          final reality = stream['realitySettings'];
          if (reality is! Map<String, dynamic>) continue;

          final fp = reality['fingerprint'];
          if (fp == null || (fp is String && fp.isEmpty)) {
            reality['fingerprint'] = 'chrome';
            modified = true;
          }
        }
      }

      return modified ? jsonEncode(decoded) : config;
    } catch (_) {
      return config; // Return unchanged if JSON parsing fails.
    }
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
