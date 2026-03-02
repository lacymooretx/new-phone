import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../models/auth.dart';
import '../models/user.dart';
import '../config/app_config.dart';
import 'api_service.dart';

/// Secure storage keys.
const _keyAccessToken = 'np_access_token';
const _keyRefreshToken = 'np_refresh_token';
const _keyServerUrl = 'np_server_url';

/// Handles authentication against the New Phone API.
///
/// Persists tokens in secure storage (Keychain on iOS, EncryptedSharedPrefs
/// on Android). Provides login, MFA verification, token refresh, and logout.
class AuthService {
  final ApiService _api;
  final FlutterSecureStorage _storage;

  String? _accessToken;
  String? _refreshToken;

  AuthService({
    required ApiService api,
    FlutterSecureStorage? storage,
  })  : _api = api,
        _storage = storage ?? const FlutterSecureStorage();

  /// Current access token, if any.
  String? get accessToken => _accessToken;

  /// Current refresh token, if any.
  String? get refreshToken => _refreshToken;

  // ---------------------------------------------------------------------------
  // Server URL persistence
  // ---------------------------------------------------------------------------

  /// Save the user-configured server URL.
  Future<void> saveServerUrl(String url) async {
    await _storage.write(key: _keyServerUrl, value: url);
  }

  /// Load the previously saved server URL, or return the default.
  Future<String> loadServerUrl() async {
    final stored = await _storage.read(key: _keyServerUrl);
    return stored ?? AppConfig.defaultApiBaseUrl;
  }

  // ---------------------------------------------------------------------------
  // Login
  // ---------------------------------------------------------------------------

  /// Authenticate with email and password.
  ///
  /// Returns [LoginSuccess] with tokens on success, or [LoginMfaRequired]
  /// if the user has MFA enabled.
  Future<LoginResult> login(LoginRequest request) async {
    final response = await _api.post<Map<String, dynamic>>(
      '/auth/login',
      data: request.toJson(),
    );

    final data = response.data!;

    // Check if MFA is required
    if (data.containsKey('mfa_session_token')) {
      return LoginMfaRequired(
        mfaSessionToken: data['mfa_session_token'] as String,
      );
    }

    // Success — store tokens
    final tokens = TokenPair.fromJson(data);
    await _persistTokens(tokens);
    return LoginSuccess(tokens: tokens);
  }

  // ---------------------------------------------------------------------------
  // MFA
  // ---------------------------------------------------------------------------

  /// Submit the MFA code to complete authentication.
  Future<TokenPair> verifyMfa(MfaRequest request) async {
    final response = await _api.post<Map<String, dynamic>>(
      '/auth/mfa/challenge',
      data: request.toJson(),
    );

    final tokens = TokenPair.fromJson(response.data!);
    await _persistTokens(tokens);
    return tokens;
  }

  // ---------------------------------------------------------------------------
  // Token refresh
  // ---------------------------------------------------------------------------

  /// Refresh the access token using the stored refresh token.
  ///
  /// Returns the new access token, or null if refresh failed.
  Future<String?> refreshTokens() async {
    final currentRefresh = _refreshToken;
    if (currentRefresh == null) return null;

    try {
      final response = await _api.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: {'refresh_token': currentRefresh},
      );

      final tokens = TokenPair.fromJson(response.data!);
      await _persistTokens(tokens);
      return tokens.accessToken;
    } catch (_) {
      // Refresh failed — clear tokens
      await clearTokens();
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // Load stored tokens
  // ---------------------------------------------------------------------------

  /// Load tokens from secure storage on app start.
  ///
  /// Returns a [User] if valid tokens are found, null otherwise.
  Future<User?> loadStoredTokens() async {
    final access = await _storage.read(key: _keyAccessToken);
    final refresh = await _storage.read(key: _keyRefreshToken);

    if (access == null || refresh == null) return null;

    _accessToken = access;
    _refreshToken = refresh;

    // Check if access token is expired (with threshold)
    if (User.isTokenExpired(
      access,
      thresholdSeconds: AppConfig.tokenRefreshThresholdSeconds,
    )) {
      // Try to refresh
      final newToken = await refreshTokens();
      if (newToken == null) return null;
      return User.fromJwt(newToken);
    }

    try {
      return User.fromJwt(access);
    } catch (_) {
      await clearTokens();
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // Logout
  // ---------------------------------------------------------------------------

  /// Clear all stored auth state.
  Future<void> logout() async {
    await clearTokens();
  }

  // ---------------------------------------------------------------------------
  // Internals
  // ---------------------------------------------------------------------------

  Future<void> _persistTokens(TokenPair tokens) async {
    _accessToken = tokens.accessToken;
    _refreshToken = tokens.refreshToken;
    await _storage.write(key: _keyAccessToken, value: tokens.accessToken);
    await _storage.write(key: _keyRefreshToken, value: tokens.refreshToken);
  }

  Future<void> clearTokens() async {
    _accessToken = null;
    _refreshToken = null;
    await _storage.delete(key: _keyAccessToken);
    await _storage.delete(key: _keyRefreshToken);
  }
}
