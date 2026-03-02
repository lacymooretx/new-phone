import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

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
  ),
  general(
    id: 'np_general',
    name: 'General',
    description: 'General notifications',
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
        if (id != null) 'id': id,
        if (route != null) 'route': route,
        ...extra,
      };

  factory NotificationPayload.fromJson(Map<String, dynamic> json) {
    final type = json['type'] as String? ?? '';
    final id = json['id'] as String?;
    final route = json['route'] as String?;

    final extra = <String, String>{};
    for (final entry in json.entries) {
      if (entry.key != 'type' && entry.key != 'id' && entry.key != 'route') {
        extra[entry.key] = entry.value.toString();
      }
    }

    return NotificationPayload(
      type: type,
      id: id,
      route: route,
      extra: extra,
    );
  }
}

/// Callback invoked when the user taps a notification.
typedef NotificationTapCallback = void Function(NotificationPayload payload);

/// Local notification management service.
///
/// Uses flutter_local_notifications for showing notifications on Android
/// and iOS. Handles notification channels, display, tap routing, and
/// notification lifecycle management.
class NotificationService {
  bool _initialized = false;
  NotificationTapCallback? _onTap;

  /// Auto-incrementing notification ID.
  int _nextId = 1;

  /// The plugin instance.
  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();

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
      const androidSettings =
          AndroidInitializationSettings('@mipmap/ic_launcher');

      const darwinSettings = DarwinInitializationSettings(
        requestAlertPermission: true,
        requestBadgePermission: true,
        requestSoundPermission: true,
        notificationCategories: [
          DarwinNotificationCategory(
            'voicemail',
            actions: [
              DarwinNotificationAction.plain(
                'play',
                'Play',
                options: <DarwinNotificationActionOption>{
                  DarwinNotificationActionOption.foreground,
                },
              ),
            ],
          ),
          DarwinNotificationCategory(
            'missed_call',
            actions: [
              DarwinNotificationAction.plain(
                'callback',
                'Call Back',
                options: <DarwinNotificationActionOption>{
                  DarwinNotificationActionOption.foreground,
                },
              ),
            ],
          ),
          DarwinNotificationCategory(
            'sms',
            actions: [
              DarwinNotificationAction.text(
                'reply',
                'Reply',
                buttonTitle: 'Send',
                placeholder: 'Type a reply...',
                options: <DarwinNotificationActionOption>{
                  DarwinNotificationActionOption.foreground,
                },
              ),
            ],
          ),
        ],
      );

      const settings = InitializationSettings(
        android: androidSettings,
        iOS: darwinSettings,
      );

      await _plugin.initialize(
        settings,
        onDidReceiveNotificationResponse: _onNotificationResponse,
      );

      // Create Android notification channels.
      final androidPlugin =
          _plugin.resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>();

      if (androidPlugin != null) {
        for (final channel in NotificationChannel.values) {
          await androidPlugin.createNotificationChannel(
            AndroidNotificationChannel(
              channel.id,
              channel.name,
              description: channel.description,
              importance: channel == NotificationChannel.calls
                  ? Importance.max
                  : Importance.high,
              enableVibration: true,
              playSound: true,
            ),
          );
        }
      }

      // Request notification permissions on Android 13+.
      if (androidPlugin != null) {
        await androidPlugin.requestNotificationsPermission();
      }

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
      category: 'voicemail',
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
      category: 'missed_call',
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
        route: '/home/messages',
      ),
      category: 'sms',
    );
  }

  // ---------------------------------------------------------------------------
  // Clear notifications
  // ---------------------------------------------------------------------------

  /// Clear all notifications for a given channel.
  ///
  /// Note: flutter_local_notifications does not support per-channel
  /// cancellation natively. We track notification IDs per channel
  /// for this purpose.
  Future<void> clearByChannel(NotificationChannel channel) async {
    try {
      final activeNotifications =
          await _plugin.getActiveNotifications();
      for (final notification in activeNotifications) {
        if (notification.channelId == channel.id && notification.id != null) {
          await _plugin.cancel(notification.id!);
        }
      }
      debugPrint('[NotificationService] clearByChannel: ${channel.name}');
    } catch (e) {
      debugPrint('[NotificationService] clearByChannel failed: $e');
    }
  }

  /// Clear a specific notification by its ID.
  Future<void> clearById(int notificationId) async {
    try {
      await _plugin.cancel(notificationId);
      debugPrint('[NotificationService] clearById: $notificationId');
    } catch (e) {
      debugPrint('[NotificationService] clearById failed: $e');
    }
  }

  /// Clear all notifications.
  Future<void> clearAll() async {
    try {
      await _plugin.cancelAll();
      debugPrint('[NotificationService] clearAll');
    } catch (e) {
      debugPrint('[NotificationService] clearAll failed: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // External tap forwarding (from PushService)
  // ---------------------------------------------------------------------------

  /// Handle a notification tap that originated from a push notification
  /// (not a local notification). This allows PushService to forward
  /// tap events through the same routing logic.
  void handleExternalTap(NotificationPayload payload) {
    _onTap?.call(payload);
  }

  // ---------------------------------------------------------------------------
  // Internals
  // ---------------------------------------------------------------------------

  Future<void> _show({
    required NotificationChannel channel,
    required String title,
    required String body,
    NotificationPayload? payload,
    String? category,
  }) async {
    if (!_initialized) {
      debugPrint(
        '[NotificationService] Not initialized, skipping notification',
      );
      return;
    }

    final id = _nextId++;

    try {
      final androidDetails = AndroidNotificationDetails(
        channel.id,
        channel.name,
        channelDescription: channel.description,
        importance: channel == NotificationChannel.calls
            ? Importance.max
            : Importance.high,
        priority: Priority.high,
        showWhen: true,
        autoCancel: true,
        category: channel == NotificationChannel.calls
            ? AndroidNotificationCategory.call
            : channel == NotificationChannel.messages
                ? AndroidNotificationCategory.message
                : null,
      );

      final darwinDetails = DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
        categoryIdentifier: category,
        threadIdentifier: channel.id,
      );

      final details = NotificationDetails(
        android: androidDetails,
        iOS: darwinDetails,
      );

      final payloadJson =
          payload != null ? jsonEncode(payload.toJson()) : null;

      await _plugin.show(
        id,
        title,
        body,
        details,
        payload: payloadJson,
      );

      debugPrint(
        '[NotificationService] show #$id [${channel.name}] $title: $body',
      );
    } catch (e) {
      debugPrint('[NotificationService] _show failed: $e');
    }
  }

  void _onNotificationResponse(NotificationResponse response) {
    final payloadStr = response.payload;
    if (payloadStr == null || payloadStr.isEmpty) {
      debugPrint('[NotificationService] Notification tapped (no payload)');
      return;
    }

    try {
      final json = jsonDecode(payloadStr) as Map<String, dynamic>;
      final payload = NotificationPayload.fromJson(json);

      debugPrint(
        '[NotificationService] Notification tapped: '
        'type=${payload.type}, route=${payload.route}',
      );

      // Handle notification actions (iOS action buttons, Android actions).
      if (response.actionId != null && response.actionId!.isNotEmpty) {
        _handleNotificationAction(
          response.actionId!,
          payload,
          response.input,
        );
        return;
      }

      _onTap?.call(payload);
    } catch (e) {
      debugPrint('[NotificationService] Failed to parse tap payload: $e');
    }
  }

  void _handleNotificationAction(
    String actionId,
    NotificationPayload payload,
    String? input,
  ) {
    debugPrint(
      '[NotificationService] Action: $actionId for ${payload.type}',
    );

    switch (actionId) {
      case 'play':
        // Play voicemail — deep link to voicemail player.
        final playPayload = NotificationPayload(
          type: payload.type,
          id: payload.id,
          route: '/home/voicemail',
          extra: {...payload.extra, 'action': 'play'},
        );
        _onTap?.call(playPayload);

      case 'callback':
        // Call back from missed call notification.
        final callbackPayload = NotificationPayload(
          type: payload.type,
          id: payload.id,
          route: payload.route,
          extra: {...payload.extra, 'action': 'callback'},
        );
        _onTap?.call(callbackPayload);

      case 'reply':
        // Reply to SMS from notification.
        if (input != null && input.isNotEmpty) {
          final replyPayload = NotificationPayload(
            type: payload.type,
            id: payload.id,
            route: '/home/messages',
            extra: {...payload.extra, 'action': 'reply', 'reply_text': input},
          );
          _onTap?.call(replyPayload);
        }

      default:
        _onTap?.call(payload);
    }
  }

  /// Clean up resources.
  void dispose() {
    _initialized = false;
    _onTap = null;
  }
}
