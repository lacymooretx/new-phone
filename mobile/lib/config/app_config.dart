/// Application configuration constants and environment handling.
enum Environment {
  development,
  staging,
  production,
}

class AppConfig {
  AppConfig._();

  static const String appName = 'New Phone';
  static const String appVersion = '0.1.0';

  static const Environment environment = Environment.development;

  /// Default API base URL. Can be overridden at runtime via server config.
  static const String defaultApiBaseUrl = 'https://localhost:8000';

  /// API path prefix.
  static const String apiPrefix = '/api/v1';

  /// Token refresh threshold in seconds. Refresh when less than this
  /// amount of time remains before expiry.
  static const int tokenRefreshThresholdSeconds = 300;

  /// Connection timeout in milliseconds.
  static const int connectTimeoutMs = 15000;

  /// Receive timeout in milliseconds.
  static const int receiveTimeoutMs = 30000;

  static bool get isDebug => environment == Environment.development;
}
