import 'package:dio/dio.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../data/datasources/vpn_remote_datasource.dart';
import 'vpn_state.dart';

/// Manages VPN connection state and profile loading.
///
/// Connection flow:
///   1. [loadProfile] — fetches GET /mobile/v1/profile with JWT.
///      On 401 the profile stays null and the UI shows "Нет подписки".
///   2. [connect] — builds `happ://add/<subscriptionUrl>` and launches it.
///      Emits [VpnConnectionStatus.launching] immediately, then
///      [VpnConnectionStatus.connected] (optimistic) after the URL is opened.
///   3. [disconnect] — resets to [VpnConnectionStatus.disconnected].
class VpnCubit extends Cubit<VpnState> {
  VpnCubit({required this.dataSource}) : super(const VpnState());

  final VpnRemoteDataSource dataSource;

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
        // Auth errors are soft: no profile, no loud error message
        error: () => isAuthError ? null : _friendlyError(e),
      ));
    } catch (_) {
      emit(state.copyWith(
        isLoadingProfile: false,
        error: () => 'Не удалось загрузить профиль',
      ));
    }
  }

  // ── Connection ────────────────────────────────────────────────────────────

  /// Launches the Happ VPN client with the user's subscription URL.
  Future<void> connect() async {
    final subscriptionUrl = state.profile?.subscriptionUrl;
    if (subscriptionUrl == null || subscriptionUrl.isEmpty) {
      emit(state.copyWith(error: () => 'Нет активной подписки'));
      return;
    }

    emit(state.copyWith(
      connectionStatus: VpnConnectionStatus.launching,
      error: () => null,
    ));

    final uri = Uri.parse('happ://add/$subscriptionUrl');
    try {
      final launched = await launchUrl(
        uri,
        mode: LaunchMode.externalApplication,
      );
      if (launched) {
        // Optimistic — user is now in Happ configuring the VPN
        emit(state.copyWith(connectionStatus: VpnConnectionStatus.connected));
      } else {
        // Happ not installed — send user to the App Store
        await _openHappStore();
        emit(state.copyWith(
          connectionStatus: VpnConnectionStatus.disconnected,
          error: () => 'Приложение Happ не установлено',
        ));
      }
    } catch (_) {
      await _openHappStore();
      emit(state.copyWith(
        connectionStatus: VpnConnectionStatus.disconnected,
        error: () => 'Установите приложение Happ для подключения',
      ));
    }
  }

  /// Marks as disconnected (does not close the VPN tunnel — that happens in Happ).
  void disconnect() {
    emit(state.copyWith(connectionStatus: VpnConnectionStatus.disconnected));
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  Future<void> _openHappStore() async {
    // Universal link — redirects to the correct store on each platform
    final storeUri = Uri.parse('https://happ.app');
    if (await canLaunchUrl(storeUri)) {
      await launchUrl(storeUri, mode: LaunchMode.externalApplication);
    }
  }

  String _friendlyError(DioException e) {
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
