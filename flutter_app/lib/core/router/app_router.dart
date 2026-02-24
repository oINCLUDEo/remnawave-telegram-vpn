import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../di/injection.dart';
import '../../features/auth/presentation/bloc/auth_bloc.dart';
import '../../features/auth/presentation/pages/login_page.dart';
import '../../features/auth/presentation/pages/register_page.dart';
import '../../features/vpn/presentation/pages/vpn_shell_page.dart';

/// Route names.
abstract class AppRoutes {
  static const login = '/login';
  static const register = '/register';
  static const home = '/home';
  static const subscription = '/subscription';
  static const serverSelection = '/servers';
  static const emailSent = '/email-sent';
}

/// Application router built with go_router.
GoRouter buildRouter() {
  return GoRouter(
    initialLocation: AppRoutes.home,
    routes: [
      // ── Hidden auth routes (kept for future Telegram/Google login) ──
      GoRoute(
        path: AppRoutes.login,
        builder: (context, state) => BlocProvider(
          create: (_) => sl<AuthBloc>(),
          child: LoginPage(
            onLoginSuccess: (_) => context.go(AppRoutes.home),
            onGoToRegister: () => context.push(AppRoutes.register),
          ),
        ),
      ),
      GoRoute(
        path: AppRoutes.register,
        builder: (context, state) => BlocProvider(
          create: (_) => sl<AuthBloc>(),
          child: RegisterPage(
            onGoToLogin: () => context.pop(),
            onRegisterSuccess: ({required requiresVerification, required email}) {
              if (requiresVerification) {
                context.go('${AppRoutes.emailSent}?email=$email');
              } else {
                context.go(AppRoutes.home);
              }
            },
          ),
        ),
      ),
      GoRoute(
        path: AppRoutes.emailSent,
        builder: (context, state) {
          final email = state.uri.queryParameters['email'] ?? '';
          return _EmailSentPage(email: email);
        },
      ),
      // ── Main app shell ──
      GoRoute(
        path: AppRoutes.home,
        builder: (context, state) => const VpnShellPage(),
      ),
    ],
  );
}

class _EmailSentPage extends StatelessWidget {
  const _EmailSentPage({required this.email});
  final String email;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.mark_email_read_rounded, size: 80, color: Color(0xFF6C63FF)),
            const SizedBox(height: 24),
            Text('Подтвердите email', style: Theme.of(context).textTheme.headlineMedium, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            Text(
              'Мы отправили письмо на\n$email\nПерейдите по ссылке в письме, чтобы активировать аккаунт.',
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            ElevatedButton(
              onPressed: () => context.go(AppRoutes.login),
              child: const Text('Перейти ко входу'),
            ),
          ],
        ),
      ),
    );
  }
}
