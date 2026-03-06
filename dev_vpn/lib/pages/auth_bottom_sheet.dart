import 'dart:async';

import 'package:flutter/material.dart';

import '../services/auth_service.dart';

/// Shows a modal bottom sheet that explains why auth is needed and triggers
/// the Telegram deep-link login flow.
///
/// Completes with `true` when the user successfully logged in,
/// `false` / null when dismissed without logging in.
Future<bool> showAuthBottomSheet(BuildContext context) async {
  final result = await showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    isDismissible: true,
    builder: (ctx) => const _AuthBottomSheet(),
  );
  return result ?? false;
}

// ── Bottom sheet ─────────────────────────────────────────────────────────────

class _AuthBottomSheet extends StatefulWidget {
  const _AuthBottomSheet();

  @override
  State<_AuthBottomSheet> createState() => _AuthBottomSheetState();
}

enum _AuthStep {
  idle,       // initial — "Login" button visible
  opening,    // waiting for deep-link launch
  waiting,    // Telegram opened, polling…
  error,      // something failed
}

class _AuthBottomSheetState extends State<_AuthBottomSheet> {
  _AuthStep _step = _AuthStep.idle;
  String? _errorMessage;
  String? _token;
  StreamSubscription<AuthResult>? _pollSub;

  @override
  void dispose() {
    _pollSub?.cancel();
    super.dispose();
  }

  // ── Login button handler ──────────────────────────────────────────────────

  Future<void> _onLoginTap() async {
    if (_step != _AuthStep.idle && _step != _AuthStep.error) return;

    setState(() {
      _step = _AuthStep.opening;
      _errorMessage = null;
    });

    final token = await AuthService.startLogin(
      onError: (msg) {
        if (mounted) {
          setState(() {
            _step = _AuthStep.error;
            _errorMessage = msg;
          });
        }
      },
    );

    if (token == null || !mounted) return;

    _token = token;
    setState(() => _step = _AuthStep.waiting);
    _startPolling(token);
  }

  void _startPolling(String token) {
    _pollSub?.cancel();
    _pollSub = AuthService.pollStatus(token).listen(
      (result) {
        if (!mounted) {
          _pollSub?.cancel();
          return;
        }
        if (result.success) {
          _pollSub?.cancel();
          Navigator.pop(context, true);
        } else if (result.error != null) {
          _pollSub?.cancel();
          setState(() {
            _step = _AuthStep.error;
            _errorMessage = result.error;
          });
        }
        // AuthResult.pending — keep polling, no UI change needed
      },
      onError: (Object e) {
        if (mounted) {
          setState(() {
            _step = _AuthStep.error;
            _errorMessage = 'Ошибка соединения. Попробуйте снова.';
          });
        }
      },
    );
  }

  // ── Build ─────────────────────────────────────────────────────────────────

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

            // ── Icon ──────────────────────────────────────────────────────
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: const Color(0xFF6C5CE7).withValues(alpha: 0.15),
                shape: BoxShape.circle,
              ),
              child: Icon(
                _step == _AuthStep.waiting
                    ? Icons.telegram
                    : Icons.lock_person_outlined,
                size: 36,
                color: _step == _AuthStep.waiting
                    ? const Color(0xFF229ED9)
                    : const Color(0xFF6C5CE7),
              ),
            ),

            const SizedBox(height: 20),

            // ── Title ────────────────────────────────────────────────────
            Text(
              _step == _AuthStep.waiting
                  ? 'Ожидаем подтверждения…'
                  : 'Нужна авторизация',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 10),

            // ── Body text ────────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Text(
                _buildBodyText(),
                style: TextStyle(
                  color: Colors.grey[400],
                  fontSize: 14,
                  height: 1.5,
                ),
                textAlign: TextAlign.center,
              ),
            ),

            const SizedBox(height: 28),

            // ── Action area ──────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: _buildActionArea(),
            ),

            // ── Subscription info row ────────────────────────────────────
            const SizedBox(height: 12),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: _buildInfoRow(),
            ),

            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  // ── Body text ─────────────────────────────────────────────────────────────

  String _buildBodyText() {
    switch (_step) {
      case _AuthStep.idle:
        return 'Для подключения к VPN-серверам необходима активная подписка. '
            'Войдите через Telegram одним касанием.';
      case _AuthStep.opening:
        return 'Открываем Telegram…';
      case _AuthStep.waiting:
        return 'Telegram открыт. Нажмите «Старт» в боте — '
            'авторизация завершится автоматически.';
      case _AuthStep.error:
        return _errorMessage ?? 'Произошла ошибка. Попробуйте снова.';
    }
  }

  // ── Action area ───────────────────────────────────────────────────────────

  Widget _buildActionArea() {
    switch (_step) {
      case _AuthStep.idle:
        return _LoginButton(onTap: _onLoginTap);
      case _AuthStep.opening:
        return const _LoadingRow(label: 'Открываем Telegram…');
      case _AuthStep.waiting:
        return Column(
          children: [
            const _LoadingRow(label: 'Ожидаем подтверждения…'),
            const SizedBox(height: 12),
            TextButton(
              onPressed: () {
                _pollSub?.cancel();
                setState(() {
                  _step = _AuthStep.idle;
                  _errorMessage = null;
                  _token = null;
                });
              },
              child: const Text(
                'Отмена',
                style: TextStyle(color: Colors.grey),
              ),
            ),
          ],
        );
      case _AuthStep.error:
        return _LoginButton(onTap: _onLoginTap, label: 'Попробовать снова');
    }
  }

  // ── Info row ──────────────────────────────────────────────────────────────

  Widget _buildInfoRow() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.amber.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.amber.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Icon(Icons.info_outline, size: 16, color: Colors.amber[300]),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'В будущем подписку можно будет купить прямо в приложении. '
              'Если подписка уже есть — просто войдите в аккаунт.',
              style: TextStyle(
                color: Colors.amber[300],
                fontSize: 12,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Shared widgets ────────────────────────────────────────────────────────────

class _LoginButton extends StatelessWidget {
  final VoidCallback onTap;
  final String label;

  const _LoginButton({
    required this.onTap,
    this.label = 'Войти через Telegram',
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: FilledButton.icon(
        onPressed: onTap,
        icon: const Icon(Icons.telegram, size: 20),
        label: Text(
          label,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
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
    );
  }
}

class _LoadingRow extends StatelessWidget {
  final String label;

  const _LoadingRow({required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            color: Color(0xFF6C5CE7),
          ),
        ),
        const SizedBox(width: 12),
        Text(label, style: const TextStyle(color: Colors.white70, fontSize: 14)),
      ],
    );
  }
}
