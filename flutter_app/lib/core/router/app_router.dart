import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../providers/auth_provider.dart';
import '../../screens/auth/login_screen.dart';
import '../../screens/auth/register_screen.dart';
import '../../screens/home/home_screen.dart';
import '../../screens/balance/balance_screen.dart';
import '../../screens/subscription/subscription_screen.dart';
import '../../screens/referral/referral_screen.dart';
import '../../screens/profile/profile_screen.dart';

class AppRouter {
  final AuthProvider authProvider;
  
  AppRouter(this.authProvider);
  
  late final GoRouter router = GoRouter(
    refreshListenable: authProvider,
    redirect: (context, state) {
      final isAuth = authProvider.isAuthenticated;
      final isAuthPage = state.matchedLocation.startsWith('/auth');
      
      if (!isAuth && !isAuthPage) {
        return '/auth/login';
      }
      if (isAuth && isAuthPage) {
        return '/';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/auth/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/auth/register',
        builder: (context, state) => const RegisterScreen(),
      ),
      GoRoute(
        path: '/',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: '/balance',
        builder: (context, state) => const BalanceScreen(),
      ),
      GoRoute(
        path: '/subscription',
        builder: (context, state) => const SubscriptionScreen(),
      ),
      GoRoute(
        path: '/referral',
        builder: (context, state) => const ReferralScreen(),
      ),
      GoRoute(
        path: '/profile',
        builder: (context, state) => const ProfileScreen(),
      ),
    ],
  );
}
