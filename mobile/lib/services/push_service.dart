import 'dart:io';

import 'package:flutter/foundation.dart';

import 'api_service.dart';
import 'callkit_service.dart';

/// Push notification service for Firebase Cloud Messaging (FCM).
///
/// Handles FCM initialization, token management, and push notification
/// routing. Incoming call pushes are forwarded to CallKit for the native
/// call UI. Other notifications (voicemail, SMS, missed call) are handed
/// to [NotificationService] for local display.
///
/// NOTE: This is the interface and implementation scaffold. The actual
/// `firebase_messaging` package is not yet in pubspec.yaml. All platform
/// calls are stubbed with debug prints until the dependency is added.
class PushService {
  final ApiService _api;
  final CallKitService _callKitService;

  String? _fcmToken;
  bool _initialized = false;

  PushService({
    required ApiService api,
    required CallKitService callKitService,
  })  : _api = api,
        _callKitService = callKitService;

  /// Current FCM token, if available.
  String? get fcmToken => _fcmToken;

  /// Whether the service has been initialized.
  bool get isInitialized => _initialized;

  // ---------------------------------------------------------------------------
  // Initialization
  // ---------------------------------------------------------------------------

  /// Initialize FCM and request notification permissions.
  ///
  /// Call this after authentication succeeds, so the token can be
  /// registered with the API server.
  Future<void> init() async {
    if (_initialized) return;

    try {
      // TODO: Initialize Firebase
      // await Firebase.initializeApp();

      // Request notification permissions (iOS)
      await _requestPermissions();

      // Get the FCM token
      _fcmToken = await getToken();

      // Listen for token refresh
      _listenForTokenRefresh();

      // Configure foreground notification handling
      _configureForegroundHandler();

      _initialized = true;
      debugPrint('[PushService] Initialized with token: ${_fcmToken?.substring(0, 20)}...');
    } catch (e) {
      debugPrint('[PushService] Init failed: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Token management
  // ---------------------------------------------------------------------------

  /// Retrieve the current FCM registration token.
  Future<String?> getToken() async {
    try {
      // TODO: final token = await FirebaseMessaging.instance.getToken();
      // _fcmToken = token;
      // return token;

      debugPrint('[PushService] getToken() — stub (firebase_messaging not installed)');
      return null;
    } catch (e) {
      debugPrint('[PushService] getToken failed: $e');
      return null;
    }
  }

  /// Register the FCM token with the API server.
  ///
  /// POST /api/v1/users/me/devices
  /// Body: { fcm_token, platform, device_name }
  Future<void> registerWithServer() async {
    final token = _fcmToken;
    if (token == null) {
      debugPrint('[PushService] No FCM token to register');
      return;
    }

    try {
      final platform = Platform.isIOS ? 'ios' : 'android';
      final deviceName = Platform.localHostname;

      await _api.post(
        '/users/me/devices',
        data: {
          'fcm_token': token,
          'platform': platform,
          'device_name': deviceName,
        },
      );

      debugPrint('[PushService] Token registered with server');
    } catch (e) {
      debugPrint('[PushService] registerWithServer failed: $e');
    }
  }

  /// Unregister the device token from the server (on logout).
  Future<void> unregisterFromServer() async {
    final token = _fcmToken;
    if (token == null) return;

    try {
      await _api.delete(
        '/users/me/devices',
        data: {'fcm_token': token},
      );
      debugPrint('[PushService] Token unregistered from server');
    } catch (e) {
      debugPrint('[PushService] unregisterFromServer failed: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Foreground message handling
  // ---------------------------------------------------------------------------

  /// Handle a push notification received while the app is in the foreground.
  ///
  /// Routes the notification based on its type:
  /// - `incoming_call` -> CallKit
  /// - `voicemail` -> local notification
  /// - `missed_call` -> local notification
  /// - `sms` -> local notification
  void handleForegroundMessage(Map<String, dynamic> data) {
    final type = data['type'] as String?;

    debugPrint('[PushService] Foreground message: type=$type');

    switch (type) {
      case 'incoming_call':
        _handleIncomingCallPush(data);

      case 'voicemail':
      case 'missed_call':
      case 'sms':
        // These will be forwarded to NotificationService by the caller
        // (typically main.dart or notification_service.dart)
        debugPrint('[PushService] Foreground notification: $type');

      default:
        debugPrint('[PushService] Unknown push type: $type');
    }
  }

  /// Handle a push notification received while the app is in the background
  /// or terminated.
  ///
  /// This is typically registered as a top-level function for FCM:
  /// `FirebaseMessaging.onBackgroundMessage(handleBackgroundMessage)`
  ///
  /// For incoming calls, this triggers CallKit so the native call UI
  /// appears even when the app is not running.
  static void handleBackgroundMessage(Map<String, dynamic> data) {
    final type = data['type'] as String?;

    debugPrint('[PushService] Background message: type=$type');

    switch (type) {
      case 'incoming_call':
        // CallKit/ConnectionService must be invoked here for the native
        // incoming call UI on the lock screen.
        //
        // On iOS, VoIP pushes via APNs + PushKit are required for reliable
        // background wake. The FCM payload triggers CallKit via the
        // flutter_callkeep plugin.
        //
        // TODO: FlutterCallkeep.displayIncomingCall(
        //   data['call_id'],
        //   data['caller_number'],
        //   callerName: data['caller_name'],
        // );
        debugPrint(
          '[PushService] Background incoming call: '
          '${data['caller_name'] ?? data['caller_number']}',
        );

      default:
        // Other notification types will show via local notifications
        // when the user opens the app.
        debugPrint('[PushService] Background notification: $type');
    }
  }

  // ---------------------------------------------------------------------------
  // Internals
  // ---------------------------------------------------------------------------

  Future<void> _requestPermissions() async {
    // TODO: Uncomment when firebase_messaging is added
    // final settings = await FirebaseMessaging.instance.requestPermission(
    //   alert: true,
    //   badge: true,
    //   sound: true,
    //   provisional: false,
    //   criticalAlert: true, // Required for VoIP on iOS
    // );
    // debugPrint('[PushService] Permission status: ${settings.authorizationStatus}');

    debugPrint('[PushService] requestPermissions() — stub');
  }

  void _listenForTokenRefresh() {
    // TODO: Uncomment when firebase_messaging is added
    // FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
    //   _fcmToken = newToken;
    //   registerWithServer(); // Re-register with new token
    //   debugPrint('[PushService] Token refreshed');
    // });

    debugPrint('[PushService] listenForTokenRefresh() — stub');
  }

  void _configureForegroundHandler() {
    // TODO: Uncomment when firebase_messaging is added
    // FirebaseMessaging.onMessage.listen((RemoteMessage message) {
    //   handleForegroundMessage(message.data);
    // });

    debugPrint('[PushService] configureForegroundHandler() — stub');
  }

  void _handleIncomingCallPush(Map<String, dynamic> data) {
    final callId = data['call_id'] as String? ?? '';
    final callerNumber = data['caller_number'] as String? ?? 'Unknown';
    final callerName = data['caller_name'] as String?;

    debugPrint(
      '[PushService] Incoming call push: '
      'callId=$callId, caller=${callerName ?? callerNumber}',
    );

    // Report to CallKit for native incoming call UI
    _callKitService.reportIncomingCall(
      callId: callId,
      callerNumber: callerNumber,
      callerName: callerName,
    );
  }

  /// Clean up resources.
  void dispose() {
    _initialized = false;
    _fcmToken = null;
  }
}
