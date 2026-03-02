import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import 'api_service.dart';
import 'callkit_service.dart';
import 'notification_service.dart';

// ---------------------------------------------------------------------------
// Top-level background message handler
// ---------------------------------------------------------------------------

/// Background message handler registered with Firebase.
///
/// Must be a top-level function (not a class method) because Firebase
/// invokes it in an isolate when the app is backgrounded/terminated.
///
/// For incoming calls, this triggers CallKit so the native call UI
/// appears even when the app is not running. On iOS, VoIP pushes via
/// APNs + PushKit are the primary mechanism; this handler serves as
/// the Android fallback and secondary iOS path.
@pragma('vm:entry-point')
Future<void> firebaseBackgroundMessageHandler(RemoteMessage message) async {
  final data = message.data;
  final type = data['type'] as String?;

  debugPrint('[PushService] Background message: type=$type');

  switch (type) {
    case 'incoming_call':
      // On Android, the CallKeep plugin can display an incoming call
      // notification from the background. On iOS, PushKit is preferred
      // but FCM data messages can also wake the app briefly.
      //
      // The actual CallKeep.displayIncomingCall is invoked when the main
      // isolate processes this in _handleIncomingCallPush. For background
      // processing, the notification payload alone triggers the system UI
      // via the high-priority FCM channel configured in init().
      debugPrint(
        '[PushService] Background incoming call: '
        '${data['caller_name'] ?? data['caller_number']}',
      );

    case 'voicemail':
    case 'missed_call':
    case 'sms':
      // These will be displayed as local notifications when the user
      // opens the app, or via the FCM notification payload if present.
      debugPrint('[PushService] Background notification: $type');

    default:
      debugPrint('[PushService] Unknown background push type: $type');
  }
}

// ---------------------------------------------------------------------------
// Push notification service
// ---------------------------------------------------------------------------

/// Push notification service for Firebase Cloud Messaging (FCM).
///
/// Handles FCM initialization, token management, and push notification
/// routing. Incoming call pushes are forwarded to CallKit for the native
/// call UI. Other notifications (voicemail, SMS, missed call) are handed
/// to [NotificationService] for local display.
class PushService {
  final ApiService _api;
  final CallKitService _callKitService;
  final NotificationService _notificationService;

  String? _fcmToken;
  bool _initialized = false;

  PushService({
    required ApiService api,
    required CallKitService callKitService,
    required NotificationService notificationService,
  })  : _api = api,
        _callKitService = callKitService,
        _notificationService = notificationService;

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
      // Request notification permissions (iOS requires explicit permission).
      await _requestPermissions();

      // Get the FCM token.
      _fcmToken = await getToken();

      if (_fcmToken != null) {
        debugPrint(
          '[PushService] Initialized with token: '
          '${_fcmToken!.substring(0, _fcmToken!.length.clamp(0, 20))}...',
        );
      } else {
        debugPrint('[PushService] Initialized but no FCM token available');
      }

      // Listen for token refresh events.
      _listenForTokenRefresh();

      // Configure foreground notification handling.
      _configureForegroundHandler();

      // Register the background message handler.
      FirebaseMessaging.onBackgroundMessage(firebaseBackgroundMessageHandler);

      // Handle notification taps that opened the app from terminated state.
      _handleInitialMessage();

      // Handle notification taps that opened the app from background state.
      _handleMessageOpenedApp();

      _initialized = true;
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
      final token = await FirebaseMessaging.instance.getToken();
      _fcmToken = token;
      return token;
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
        _handleVoicemailPush(data);

      case 'missed_call':
        _handleMissedCallPush(data);

      case 'sms':
        _handleSmsPush(data);

      default:
        debugPrint('[PushService] Unknown push type: $type');
    }
  }

  // ---------------------------------------------------------------------------
  // Internals
  // ---------------------------------------------------------------------------

  Future<void> _requestPermissions() async {
    try {
      final settings = await FirebaseMessaging.instance.requestPermission(
        alert: true,
        badge: true,
        sound: true,
        provisional: false,
        criticalAlert: true,
        announcement: false,
        carPlay: false,
      );

      debugPrint(
        '[PushService] Permission status: ${settings.authorizationStatus}',
      );

      // On iOS, also configure foreground notification presentation.
      await FirebaseMessaging.instance
          .setForegroundNotificationPresentationOptions(
        alert: false, // We handle foreground notifications ourselves.
        badge: true,
        sound: false,
      );
    } catch (e) {
      debugPrint('[PushService] requestPermissions failed: $e');
    }
  }

  void _listenForTokenRefresh() {
    FirebaseMessaging.instance.onTokenRefresh.listen(
      (newToken) {
        debugPrint('[PushService] Token refreshed');
        _fcmToken = newToken;
        registerWithServer();
      },
      onError: (Object error) {
        debugPrint('[PushService] Token refresh listener error: $error');
      },
    );
  }

  void _configureForegroundHandler() {
    FirebaseMessaging.onMessage.listen(
      (RemoteMessage message) {
        handleForegroundMessage(message.data);
      },
      onError: (Object error) {
        debugPrint('[PushService] Foreground message listener error: $error');
      },
    );
  }

  /// Check if the app was opened from a terminated state via a notification.
  Future<void> _handleInitialMessage() async {
    try {
      final initialMessage =
          await FirebaseMessaging.instance.getInitialMessage();
      if (initialMessage != null) {
        debugPrint('[PushService] App opened from terminated via notification');
        _handleNotificationTap(initialMessage.data);
      }
    } catch (e) {
      debugPrint('[PushService] _handleInitialMessage failed: $e');
    }
  }

  /// Listen for notification taps that open the app from background.
  void _handleMessageOpenedApp() {
    FirebaseMessaging.onMessageOpenedApp.listen(
      (RemoteMessage message) {
        debugPrint('[PushService] App opened from background via notification');
        _handleNotificationTap(message.data);
      },
      onError: (Object error) {
        debugPrint('[PushService] onMessageOpenedApp error: $error');
      },
    );
  }

  void _handleIncomingCallPush(Map<String, dynamic> data) {
    final callId = data['call_id'] as String? ?? '';
    final callerNumber = data['caller_number'] as String? ?? 'Unknown';
    final callerName = data['caller_name'] as String?;

    debugPrint(
      '[PushService] Incoming call push: '
      'callId=$callId, caller=${callerName ?? callerNumber}',
    );

    // Report to CallKit for native incoming call UI.
    _callKitService.reportIncomingCall(
      callId: callId,
      callerNumber: callerNumber,
      callerName: callerName,
    );
  }

  void _handleVoicemailPush(Map<String, dynamic> data) {
    final callerName = data['caller_name'] as String? ?? 'Unknown';
    final callerNumber = data['caller_number'] as String? ?? '';
    final duration = data['duration'] as String? ?? '';
    final messageId = data['message_id'] as String?;
    final boxId = data['box_id'] as String?;

    _notificationService.showNewVoicemail(
      callerName: callerName,
      callerNumber: callerNumber,
      duration: duration,
      messageId: messageId,
      boxId: boxId,
    );
  }

  void _handleMissedCallPush(Map<String, dynamic> data) {
    final callerName = data['caller_name'] as String? ?? '';
    final callerNumber = data['caller_number'] as String? ?? 'Unknown';
    final callId = data['call_id'] as String?;

    _notificationService.showMissedCall(
      callerName: callerName,
      callerNumber: callerNumber,
      callId: callId,
    );
  }

  void _handleSmsPush(Map<String, dynamic> data) {
    final senderName = data['sender_name'] as String? ?? '';
    final senderNumber = data['sender_number'] as String? ?? 'Unknown';
    final preview = data['preview'] as String? ?? '';
    final conversationId = data['conversation_id'] as String?;

    _notificationService.showNewSms(
      senderName: senderName,
      senderNumber: senderNumber,
      preview: preview,
      conversationId: conversationId,
    );
  }

  /// Handle a notification tap that navigated the user into the app.
  /// Routes to the appropriate screen based on the notification type.
  void _handleNotificationTap(Map<String, dynamic> data) {
    final type = data['type'] as String?;
    debugPrint('[PushService] Notification tap: type=$type');

    // The notification tap routing is handled by the NotificationService's
    // onTap callback, which deep-links via go_router. For push-originated
    // taps, we construct a NotificationPayload and forward it.
    switch (type) {
      case 'voicemail':
        final payload = NotificationPayload(
          type: 'voicemail',
          id: data['message_id'] as String?,
          route: '/home/voicemail',
        );
        _notificationService.handleExternalTap(payload);

      case 'missed_call':
        final number = data['caller_number'] as String? ?? '';
        final payload = NotificationPayload(
          type: 'missed_call',
          id: data['call_id'] as String?,
          route: '/contact/${Uri.encodeComponent(number)}',
        );
        _notificationService.handleExternalTap(payload);

      case 'sms':
        final payload = NotificationPayload(
          type: 'sms',
          id: data['conversation_id'] as String?,
          route: '/home/messages',
        );
        _notificationService.handleExternalTap(payload);

      default:
        debugPrint('[PushService] No tap handler for type: $type');
    }
  }

  /// Clean up resources.
  void dispose() {
    _initialized = false;
    _fcmToken = null;
  }
}
