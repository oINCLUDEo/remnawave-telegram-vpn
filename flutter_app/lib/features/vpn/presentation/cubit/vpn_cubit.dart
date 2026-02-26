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

      // Fetch subscription and parse proxy configs
      final configs = await FlutterV2ray.parseUrl(subscriptionUrl);
      if (configs.isEmpty) {
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.error,
          error: () => 'Конфигурация VPN недоступна',
        ));
        return;
      }

      // Pick the first available config (TODO: allow server selection)
      final selected = configs.first;

      await _v2ray.startV2Ray(
        remark: selected.remark,
        config: selected.getFullConfig(bypassSubnets: []),
        proxyOnly: false,
        bypassSubnets: [],
        notificationDisconnectButtonName: 'Отключить',
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
