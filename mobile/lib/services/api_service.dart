import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../config/app_config.dart';

/// Callback to retrieve the current access token.
typedef TokenGetter = Future<String?> Function();

/// Callback to refresh the token pair. Returns the new access token
/// or null if refresh failed (triggers logout).
typedef TokenRefresher = Future<String?> Function();

/// Callback invoked when auth is irrecoverably invalid (e.g. refresh fails).
typedef LogoutCallback = Future<void> Function();

/// Dio-based HTTP client with token management and logging.
class ApiService {
  late final Dio _dio;

  TokenGetter? _getToken;
  TokenRefresher? _refreshToken;
  LogoutCallback? _onLogout;

  /// Whether a token refresh is currently in progress.
  bool _isRefreshing = false;

  ApiService({required String baseUrl}) {
    _dio = Dio(
      BaseOptions(
        baseUrl: '$baseUrl${AppConfig.apiPrefix}',
        connectTimeout: const Duration(
          milliseconds: AppConfig.connectTimeoutMs,
        ),
        receiveTimeout: const Duration(
          milliseconds: AppConfig.receiveTimeoutMs,
        ),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    _dio.interceptors.add(_authInterceptor());

    if (AppConfig.isDebug) {
      _dio.interceptors.add(
        LogInterceptor(
          requestHeader: true,
          requestBody: true,
          responseHeader: false,
          responseBody: true,
          logPrint: (obj) => debugPrint('[API] $obj'),
        ),
      );
    }
  }

  /// Configure auth callbacks. Must be called after auth service is ready.
  void configureAuth({
    required TokenGetter getToken,
    required TokenRefresher refreshToken,
    required LogoutCallback onLogout,
  }) {
    _getToken = getToken;
    _refreshToken = refreshToken;
    _onLogout = onLogout;
  }

  /// Update the base URL at runtime (e.g. user changes server).
  void updateBaseUrl(String baseUrl) {
    _dio.options.baseUrl = '$baseUrl${AppConfig.apiPrefix}';
  }

  /// Access the raw Dio instance for advanced use cases.
  Dio get dio => _dio;

  // ---------------------------------------------------------------------------
  // Convenience HTTP methods
  // ---------------------------------------------------------------------------

  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) =>
      _dio.get<T>(path, queryParameters: queryParameters, options: options);

  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) =>
      _dio.post<T>(path, data: data, queryParameters: queryParameters, options: options);

  Future<Response<T>> put<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) =>
      _dio.put<T>(path, data: data, queryParameters: queryParameters, options: options);

  Future<Response<T>> patch<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) =>
      _dio.patch<T>(path, data: data, queryParameters: queryParameters, options: options);

  Future<Response<T>> delete<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) =>
      _dio.delete<T>(path, data: data, queryParameters: queryParameters, options: options);

  // ---------------------------------------------------------------------------
  // Interceptors
  // ---------------------------------------------------------------------------

  InterceptorsWrapper _authInterceptor() => InterceptorsWrapper(
        onRequest: (options, handler) async {
          // Skip auth header for auth endpoints
          final path = options.path;
          if (path.contains('/auth/login') ||
              path.contains('/auth/mfa/challenge') ||
              path.contains('/auth/refresh')) {
            return handler.next(options);
          }

          final token = await _getToken?.call();
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }

          return handler.next(options);
        },
        onError: (error, handler) async {
          if (error.response?.statusCode != 401) {
            return handler.next(error);
          }

          // Don't retry auth endpoints
          final path = error.requestOptions.path;
          if (path.contains('/auth/login') ||
              path.contains('/auth/mfa/challenge') ||
              path.contains('/auth/refresh')) {
            return handler.next(error);
          }

          // Attempt token refresh
          if (_isRefreshing) {
            return handler.next(error);
          }

          _isRefreshing = true;
          try {
            final newToken = await _refreshToken?.call();
            _isRefreshing = false;

            if (newToken == null) {
              await _onLogout?.call();
              return handler.next(error);
            }

            // Retry the original request with the new token
            final opts = error.requestOptions;
            opts.headers['Authorization'] = 'Bearer $newToken';
            final response = await _dio.fetch(opts);
            return handler.resolve(response);
          } catch (_) {
            _isRefreshing = false;
            await _onLogout?.call();
            return handler.next(error);
          }
        },
      );
}
