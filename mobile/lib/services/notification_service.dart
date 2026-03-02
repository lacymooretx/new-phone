import 'package:flutter/foundation.dart';

/// Notification channel identifiers.
enum NotificationChannel {
  calls(
    id: 'np_calls',
    name: 'Calls',
    description: 'Incoming and missed call notifications',
  ),
  voicemail(
    id: 'np_voicemail',
    name: 'Voicemail',
    description: 'New voicemail notifications',
  ),
  messages(
    id: 'np_messages',
    name: 'Messages',
    description: 'New SMS/MMS message notifications',
  );

  final String id;
  final String name;
  final String description;

  const NotificationChannel({
    required this.id,
    required this.name,
    required this.description,
  });
}

/// Payload attached to a local notification for tap-to-navigate.
class NotificationPayload {
  final String type;
  final String? id;
  final String? route;
  final Map<String, String> extra;

  const NotificationPayload({
    required this.type,
    this.id,
    this.route,
    this.extra = const {},
  });

  Map<String, dynamic> toJson() => {
        'type': type,
        'id': id,
        'route': route,
        ...extra,
      };

  factory NotificationPayload.fromJson(Map<String, dynamic> json) =>
      NotificationPayload(
        type: json['type'] as String? ?? '',
        id: json['id'] as String?,
        route: json['route'] as String?,
        extra: Map<String, String>.from(
          (json..remove('type')..remove('id')..remove('route')).map(
            (k, v) => MapEntry(k, v.toString()),
          ),
        ),
      );
}

/// Callback invoked when the user taps a notification.
typedef NotificationTapCallback = void Function(NotificationPayload payload);

/// Local notification management service.
///
/// Uses flutter_local_notifications concepts for showing notifications
/// on Android and iOS. Handles notification channels, display, and tap
/// routing.
///
/// NOTE: The actual `flutter_local_notifications` package is not yet in
/// pubspec.yaml. All platform calls are stubbed with debug prints until
/// the dependency is added.
class NotificationService {
  bool _initialized = false;
  NotificationTapCallback? _onTap;

  /// Auto-incrementing notification ID.
  int _nextId = 1;

  /// Whether the service has been initialized.
  bool get isInitialized => _initialized;

  // ---------------------------------------------------------------------------
  // Initialization
  // ---------------------------------------------------------------------------

  /// Initialize local notifications.
  ///
  /// Creates notification channels (Android) and requests permissions (iOS).
  /// Call once during app startup.
  Future<void> init() async {
    if (_initialized) return;

    try {
      // TODO: Uncomment when flutter_local_notifications is added
      // final plugin = FlutterLocalNotificationsPlugin();
      //
      // const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
      // const iosSettings = DarwinInitializationSettings(
      //   requestAlertPermission: true,
      //   requestBadgePermission: true,
      //   requestSoundPermission: true,
      // );
      //
      // const settings = InitializationSettings(
      //   android: androidSettings,
      //   iOS: iosSettings,
      // );
      //
      // await plugin.initialize(
      //   settings,
      //   onDidReceiveNotificationResponse: _onNotificationTap,
      // );
      //
      // // Create Android notification channels
      // for (final channel in NotificationChannel.values) {
      //   await plugin
      //       .resolvePlatformSpecificImplementation<
      //           AndroidFlutterLocalNotificationsPlugin>()
      //       ?.createNotificationChannel(
      //         AndroidNotificationChannel(
      //           channel.id,
      //           channel.name,
      //           description: channel.description,
      //           importance: Importance.high,
      //         ),
      //       );
      // }

      _initialized = true;
      debugPrint('[NotificationService] Initialized');
    } catch (e) {
      debugPrint('[NotificationService] Init failed: $e');
    }
  }

  /// Register a callback for notification taps.
  void setOnTapCallback(NotificationTapCallback callback) {
    _onTap = callback;
  }

  // ---------------------------------------------------------------------------
  // Show notifications
  // ---------------------------------------------------------------------------

  /// Show a notification for a new voicemail.
  Future<void> showNewVoicemail({
    required String callerName,
    required String callerNumber,
    required String duration,
    String? messageId,
    String? boxId,
  }) async {
    await _show(
      channel: NotificationChannel.voicemail,
      title: 'New Voicemail',
      body: '$callerName ($callerNumber) - $duration',
      payload: NotificationPayload(
        type: 'voicemail',
        id: messageId,
        route: '/home/voicemail',
        extra: {
          if (boxId != null) 'box_id': boxId,
        },
      ),
    );
  }

  /// Show a notification for a missed call.
  Future<void> showMissedCall({
    required String callerName,
    required String callerNumber,
    String? callId,
  }) async {
    await _show(
      channel: NotificationChannel.calls,
      title: 'Missed Call',
      body: callerName.isNotEmpty ? callerName : callerNumber,
      payload: NotificationPayload(
        type: 'missed_call',
        id: callId,
        route: '/contact/${Uri.encodeComponent(callerNumber)}',
      ),
    );
  }

  /// Show a notification for a new SMS/MMS message.
  Future<void> showNewSms({
    required String senderName,
    required String senderNumber,
    required String preview,
    String? conversationId,
  }) async {
    await _show(
      channel: NotificationChannel.messages,
      title: senderName.isNotEmpty ? senderName : senderNumber,
      body: preview,
      payload: NotificationPayload(
        type: 'sms',
        id: conversationId,
        route: '/home/messages', // Future SMS screen
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Clear notifications
  // ---------------------------------------------------------------------------

  /// Clear all notifications for a given channel.
  Future<void> clearByChannel(NotificationChannel channel) async {
    // TODO: Uncomment when flutter_local_notifications is added
    // final plugin = FlutterLocalNotificationsPlugin();
    // await plugin.cancelAll(); // Would need per-channel tracking
    debugPrint('[NotificationService] clearByChannel: ${channel.name}');
  }

  /// Clear a specific notification by its ID.
  Future<void> clearById(int notificationId) async {
    // TODO: Uncomment when flutter_local_notifications is added
    // final plugin = FlutterLocalNotificationsPlugin();
    // await plugin.cancel(notificationId);
    debugPrint('[NotificationService] clearById: $notificationId');
  }

  /// Clear all notifications.
  Future<void> clearAll() async {
    // TODO: Uncomment when flutter_local_notifications is added
    // final plugin = FlutterLocalNotificationsPlugin();
    // await plugin.cancelAll();
    debugPrint('[NotificationService] clearAll');
  }

  // ---------------------------------------------------------------------------
  // Internals
  // ---------------------------------------------------------------------------

  Future<void> _show({
    required NotificationChannel channel,
    required String title,
    required String body,
    NotificationPayload? payload,
  }) async {
    final id = _nextId++;

    // TODO: Uncomment when flutter_local_notifications is added
    // final plugin = FlutterLocalNotificationsPlugin();
    //
    // final androidDetails = AndroidNotificationDetails(
    //   channel.id,
    //   channel.name,
    //   channelDescription: channel.description,
    //   importance: Importance.high,
    //   priority: Priority.high,
    //   showWhen: true,
    // );
    //
    // final iosDetails = const DarwinNotificationDetails(
    //   presentAlert: true,
    //   presentBadge: true,
    //   presentSound: true,
    // );
    //
    // final details = NotificationDetails(
    //   android: androidDetails,
    //   iOS: iosDetails,
    // );
    //
    // await plugin.show(
    //   id,
    //   title,
    //   body,
    //   details,
    //   payload: payload != null ? jsonEncode(payload.toJson()) : null,
    // );

    debugPrint(
      '[NotificationService] show #$id [${channel.name}] $title: $body',
    );
  }

  void _onNotificationTap(dynamic response) {
    // TODO: Uncomment when flutter_local_notifications is added
    // final payloadStr = response.payload as String?;
    // if (payloadStr == null || payloadStr.isEmpty) return;
    //
    // try {
    //   final json = jsonDecode(payloadStr) as Map<String, dynamic>;
    //   final payload = NotificationPayload.fromJson(json);
    //   _onTap?.call(payload);
    // } catch (e) {
    //   debugPrint('[NotificationService] Failed to parse tap payload: $e');
    // }

    debugPrint('[NotificationService] Notification tapped');
  }

  /// Clean up resources.
  void dispose() {
    _initialized = false;
    _onTap = null;
  }
}
