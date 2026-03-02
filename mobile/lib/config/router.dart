import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/cdr.dart';
import '../providers/auth_provider.dart';
import '../screens/splash_screen.dart';
import '../screens/login_screen.dart';
import '../screens/mfa_screen.dart';
import '../screens/home_screen.dart';
import '../screens/call_history_screen.dart';
import '../screens/voicemail_screen.dart';
import '../screens/contacts_screen.dart';
import '../screens/settings_screen.dart';
import '../screens/contact_detail_screen.dart';
import '../screens/dialer_screen.dart';
import '../screens/active_call_screen.dart';
import '../screens/change_password_screen.dart';
import '../screens/incoming_call_screen.dart';
import '../screens/sms_conversations_screen.dart';
import '../screens/sms_thread_screen.dart';

/// GoRouter configuration with auth-aware redirects.
final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/splash',
    debugLogDiagnostics: true,
    redirect: (context, state) {
      final location = state.uri.toString();
      final isOnSplash = location == '/splash';
      final isOnLogin = location == '/login';
      final isOnMfa = location == '/mfa';
      final isAuthRoute = isOnSplash || isOnLogin || isOnMfa;

      switch (authState) {
        case AuthInitial():
        case AuthLoading():
          // While initializing, stay on splash
          return isOnSplash ? null : '/splash';

        case AuthUnauthenticated():
          // Must go to login if not already there
          return isOnLogin ? null : '/login';

        case AuthMfaRequired():
          // Must go to MFA if not already there
          return isOnMfa ? null : '/mfa';

        case AuthAuthenticated():
          // Authenticated users shouldn't be on auth routes
          if (isAuthRoute) return '/home/calls';
          // Allow call routes and home routes
          return null;
      }
    },
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/mfa',
        builder: (context, state) => const MfaScreen(),
      ),

      // Contact detail — full screen over home
      GoRoute(
        path: '/contact/:number',
        builder: (context, state) {
          final number = Uri.decodeComponent(
            state.pathParameters['number'] ?? '',
          );
          final cdr = state.extra as Cdr?;
          return ContactDetailScreen(
            phoneNumber: number,
            initialCdr: cdr,
          );
        },
      ),

      // Dialer — full screen over home
      GoRoute(
        path: '/dialer',
        builder: (context, state) => const DialerScreen(),
      ),

      // Call screens — full screen, no bottom nav
      GoRoute(
        path: '/call/active',
        builder: (context, state) => const ActiveCallScreen(),
      ),
      GoRoute(
        path: '/call/incoming',
        builder: (context, state) => const IncomingCallScreen(),
      ),

      // SMS thread — full screen over home
      GoRoute(
        path: '/sms/:conversationId',
        builder: (context, state) {
          final conversationId = state.pathParameters['conversationId'] ?? '';
          return SmsThreadScreen(conversationId: conversationId);
        },
      ),

      // Settings sub-routes — full screen over home
      GoRoute(
        path: '/settings/change-password',
        builder: (context, state) => const ChangePasswordScreen(),
      ),

      // Home shell with bottom navigation
      ShellRoute(
        builder: (context, state, child) => HomeScreen(child: child),
        routes: [
          GoRoute(
            path: '/home',
            redirect: (context, state) {
              // Redirect bare /home to /home/calls
              if (state.uri.toString() == '/home') {
                return '/home/calls';
              }
              return null;
            },
            routes: [
              GoRoute(
                path: 'calls',
                pageBuilder: (context, state) => const NoTransitionPage(
                  child: CallHistoryScreen(),
                ),
              ),
              GoRoute(
                path: 'voicemail',
                pageBuilder: (context, state) => const NoTransitionPage(
                  child: VoicemailScreen(),
                ),
              ),
              GoRoute(
                path: 'messages',
                pageBuilder: (context, state) => const NoTransitionPage(
                  child: SmsConversationsScreen(),
                ),
              ),
              GoRoute(
                path: 'contacts',
                pageBuilder: (context, state) => const NoTransitionPage(
                  child: ContactsScreen(),
                ),
              ),
              GoRoute(
                path: 'settings',
                pageBuilder: (context, state) => const NoTransitionPage(
                  child: SettingsScreen(),
                ),
              ),
            ],
          ),
        ],
      ),
    ],
  );
});
