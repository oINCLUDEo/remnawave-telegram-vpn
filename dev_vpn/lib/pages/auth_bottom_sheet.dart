import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../config/app_config.dart';
import '../services/auth_service.dart';

/// Shows a modal bottom sheet that explains why auth is needed and triggers
/// the Telegram Login Widget flow.
///
/// Completes with `true` when the user successfully logged in,
/// `false` / null when dismissed without logging in.
Future<bool> showAuthBottomSheet(BuildContext context) async {
  final result = await showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (ctx) => const _AuthBottomSheet(),
  );
  return result ?? false;
}

// ── Bottom sheet ─────────────────────────────────────────────────────────────

class _AuthBottomSheet extends StatelessWidget {
  const _AuthBottomSheet();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFF171A21),
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 12),
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey[700],
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 24),
            // Icon
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: const Color(0xFF6C5CE7).withValues(alpha: 0.15),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.lock_person_outlined,
                size: 36,
                color: Color(0xFF6C5CE7),
              ),
            ),
            const SizedBox(height: 20),
            const Text(
              'Нужна авторизация',
              style: TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 10),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Text(
                'Для подключения к VPN-серверам необходима активная подписка. '
                'Войдите через Telegram, чтобы использовать свой аккаунт.',
                style: TextStyle(
                  color: Colors.grey[400],
                  fontSize: 14,
                  height: 1.5,
                ),
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(height: 28),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: () async {
                    final loggedIn = await Navigator.push<bool>(
                      context,
                      MaterialPageRoute(
                        builder: (_) => const _TelegramAuthWebViewPage(),
                      ),
                    );
                    if (context.mounted) {
                      Navigator.pop(context, loggedIn ?? false);
                    }
                  },
                  icon: const Icon(Icons.telegram, size: 20),
                  label: const Text(
                    'Войти через Telegram',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                  ),
                  style: FilledButton.styleFrom(
                    backgroundColor: const Color(0xFF229ED9), // Telegram blue
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            // Subscription info row
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  color: Colors.amber.withValues(alpha: 0.07),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: Colors.amber.withValues(alpha: 0.2),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.info_outline,
                      size: 16,
                      color: Colors.amber[300],
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Подписка приобретается в Telegram-боте. '
                        'Если она уже есть — войдите в аккаунт.',
                        style: TextStyle(
                          color: Colors.amber[300],
                          fontSize: 12,
                          height: 1.4,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}

// ── WebView page ──────────────────────────────────────────────────────────────

/// Full-screen page hosting the Telegram Login Widget via a WebView.
class _TelegramAuthWebViewPage extends StatefulWidget {
  const _TelegramAuthWebViewPage();

  @override
  State<_TelegramAuthWebViewPage> createState() =>
      _TelegramAuthWebViewPageState();
}

class _TelegramAuthWebViewPageState extends State<_TelegramAuthWebViewPage> {
  late final WebViewController _controller;
  bool _isLoading = true;
  String? _error;
  bool _isAuthenticating = false;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) => setState(() => _isLoading = true),
          onPageFinished: (_) => setState(() => _isLoading = false),
          onWebResourceError: (err) {
            if (mounted) {
              setState(() {
                _isLoading = false;
                _error = 'Не удалось загрузить страницу авторизации.\n'
                    'Проверьте интернет-соединение.';
              });
            }
          },
        ),
      )
      ..addJavaScriptChannel(
        'TelegramAuthChannel',
        onMessageReceived: _onTelegramAuthData,
      )
      ..loadRequest(
        Uri.parse('${AppConfig.backendBaseUrl}/mobile/v1/auth/widget-page'),
      );
  }

  Future<void> _onTelegramAuthData(JavaScriptMessage message) async {
    if (_isAuthenticating) return;
    setState(() => _isAuthenticating = true);

    try {
      final data = jsonDecode(message.message) as Map<String, dynamic>;
      final error = await AuthService.loginWithWidgetData(data);
      if (!mounted) return;

      if (error == null) {
        // Success
        Navigator.pop(context, true);
      } else {
        setState(() {
          _isAuthenticating = false;
          _error = error;
        });
      }
    } on Exception catch (e) {
      if (!mounted) return;
      setState(() {
        _isAuthenticating = false;
        _error = 'Ошибка авторизации: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F0F1A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF171A21),
        foregroundColor: Colors.white,
        title: const Text(
          'Войти через Telegram',
          style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
        ),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => Navigator.pop(context, false),
        ),
        elevation: 0,
      ),
      body: Stack(
        children: [
          if (_error != null)
            _ErrorView(
              message: _error!,
              onRetry: () {
                setState(() => _error = null);
                _controller.reload();
              },
            )
          else
            WebViewWidget(controller: _controller),
          if (_isLoading && _error == null)
            const Center(
              child: CircularProgressIndicator(
                color: Color(0xFF6C5CE7),
              ),
            ),
          if (_isAuthenticating)
            Container(
              color: Colors.black54,
              child: const Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: Color(0xFF6C5CE7)),
                    SizedBox(height: 16),
                    Text(
                      'Проверка данных…',
                      style: TextStyle(color: Colors.white70, fontSize: 14),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

// ── Error view ────────────────────────────────────────────────────────────────

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorView({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.cloud_off, size: 48, color: Colors.grey[600]),
            const SizedBox(height: 16),
            Text(
              message,
              style: TextStyle(
                color: Colors.grey[400],
                fontSize: 14,
                height: 1.5,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Повторить'),
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF6C5CE7),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
