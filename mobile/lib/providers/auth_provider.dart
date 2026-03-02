import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/auth.dart';
import '../models/user.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../config/app_config.dart';

// ---------------------------------------------------------------------------
// Auth state
// ---------------------------------------------------------------------------

/// Represents the current authentication state of the app.
sealed class AuthState {
  const AuthState();
}

/// Initial state — haven't checked stored tokens yet.
class AuthInitial extends AuthState {
  const AuthInitial();
}

/// Checking stored tokens / refreshing.
class AuthLoading extends AuthState {
  const AuthLoading();
}

/// Not authenticated — show login screen.
class AuthUnauthenticated extends AuthState {
  final String? errorMessage;

  const AuthUnauthenticated({this.errorMessage});
}

/// Login succeeded but MFA is required.
class AuthMfaRequired extends AuthState {
  final String sessionToken;

  const AuthMfaRequired({required this.sessionToken});
}

/// Fully authenticated.
class AuthAuthenticated extends AuthState {
  final User user;
  final TokenPair tokens;

  const AuthAuthenticated({required this.user, required this.tokens});
}

// ---------------------------------------------------------------------------
// Providers for services
// ---------------------------------------------------------------------------

/// The API service singleton.
final apiServiceProvider = Provider<ApiService>((ref) {
  return ApiService(baseUrl: AppConfig.defaultApiBaseUrl);
});

/// The auth service singleton.
final authServiceProvider = Provider<AuthService>((ref) {
  final api = ref.watch(apiServiceProvider);
  return AuthService(api: api);
});

// ---------------------------------------------------------------------------
// Auth state notifier
// ---------------------------------------------------------------------------

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final authService = ref.watch(authServiceProvider);
  final apiService = ref.watch(apiServiceProvider);
  return AuthNotifier(authService: authService, apiService: apiService);
});

class AuthNotifier extends StateNotifier<AuthState> {
  final AuthService _authService;
  final ApiService _apiService;

  AuthNotifier({
    required AuthService authService,
    required ApiService apiService,
  })  : _authService = authService,
        _apiService = apiService,
        super(const AuthInitial()) {
    _configureApiCallbacks();
  }

  /// Wire up the API service's token/refresh/logout callbacks.
  void _configureApiCallbacks() {
    _apiService.configureAuth(
      getToken: () async => _authService.accessToken,
      refreshToken: () async => _authService.refreshTokens(),
      onLogout: () async => await logout(),
    );
  }

  /// Initialize auth by checking secure storage for existing tokens.
  Future<void> init() async {
    state = const AuthLoading();

    // Load and apply saved server URL
    final serverUrl = await _authService.loadServerUrl();
    _apiService.updateBaseUrl(serverUrl);

    final user = await _authService.loadStoredTokens();
    if (user != null) {
      state = AuthAuthenticated(
        user: user,
        tokens: TokenPair(
          accessToken: _authService.accessToken!,
          refreshToken: _authService.refreshToken!,
        ),
      );
    } else {
      state = const AuthUnauthenticated();
    }
  }

  /// Update the server URL and persist it.
  Future<void> setServerUrl(String url) async {
    _apiService.updateBaseUrl(url);
    await _authService.saveServerUrl(url);
  }

  /// Attempt login with email and password.
  Future<void> login(String email, String password) async {
    state = const AuthLoading();

    try {
      final result = await _authService.login(
        LoginRequest(email: email, password: password),
      );

      switch (result) {
        case LoginSuccess(:final tokens):
          final user = User.fromJwt(tokens.accessToken);
          state = AuthAuthenticated(user: user, tokens: tokens);

        case LoginMfaRequired(:final mfaSessionToken):
          state = AuthMfaRequired(sessionToken: mfaSessionToken);
      }
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      state = AuthUnauthenticated(errorMessage: message);
    } catch (e) {
      state = AuthUnauthenticated(errorMessage: e.toString());
    }
  }

  /// Verify MFA code.
  Future<void> verifyMfa(String sessionToken, String code) async {
    final previousState = state;
    state = const AuthLoading();

    try {
      final tokens = await _authService.verifyMfa(
        MfaRequest(sessionToken: sessionToken, code: code),
      );
      final user = User.fromJwt(tokens.accessToken);
      state = AuthAuthenticated(user: user, tokens: tokens);
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      // Restore MFA state so the user can retry
      if (previousState is AuthMfaRequired) {
        state = AuthMfaRequired(sessionToken: previousState.sessionToken);
      } else {
        state = AuthUnauthenticated(errorMessage: message);
      }
      // Re-throw so the screen can show the error
      throw AuthException(message);
    } catch (e) {
      if (previousState is AuthMfaRequired) {
        state = AuthMfaRequired(sessionToken: previousState.sessionToken);
      } else {
        state = AuthUnauthenticated(errorMessage: e.toString());
      }
      throw AuthException(e.toString());
    }
  }

  /// Log out and clear all stored credentials.
  Future<void> logout() async {
    await _authService.logout();
    state = const AuthUnauthenticated();
  }

  /// Extract a human-readable error message from a Dio error.
  String _extractErrorMessage(DioException e) {
    if (e.response?.data is Map<String, dynamic>) {
      final data = e.response!.data as Map<String, dynamic>;
      if (data.containsKey('detail')) {
        final detail = data['detail'];
        if (detail is String) return detail;
        if (detail is List && detail.isNotEmpty) {
          return detail.map((d) => d['msg'] ?? d.toString()).join(', ');
        }
      }
    }

    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return 'Connection timed out. Check your network and server address.';
      case DioExceptionType.connectionError:
        return 'Could not connect to server. Verify the server address.';
      case DioExceptionType.badResponse:
        final code = e.response?.statusCode;
        if (code == 401) return 'Invalid email or password.';
        if (code == 403) return 'Access denied.';
        if (code == 422) return 'Invalid request. Check your input.';
        if (code != null && code >= 500) return 'Server error. Try again later.';
        return 'Request failed (HTTP $code).';
      default:
        return 'An unexpected error occurred.';
    }
  }
}

/// Exception thrown by auth operations for UI consumption.
class AuthException implements Exception {
  final String message;
  const AuthException(this.message);

  @override
  String toString() => message;
}
