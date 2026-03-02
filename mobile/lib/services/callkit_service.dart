import 'dart:async';

import 'package:flutter/foundation.dart';

// ---------------------------------------------------------------------------
// CallKit / ConnectionService abstraction
// ---------------------------------------------------------------------------

/// Actions the system call UI can trigger (answer from lock screen, etc.).
enum SystemCallAction {
  answer,
  end,
  hold,
  unhold,
  mute,
  unmute,
}

/// Callback signature for system call actions.
typedef SystemCallActionCallback = void Function(
  String callId,
  SystemCallAction action,
);

/// Abstraction over iOS CallKit and Android ConnectionService.
///
/// On iOS this drives the native incoming-call UI (works even when the app is
/// backgrounded or the device is locked). On Android it integrates with
/// ConnectionService for a similar experience.
///
/// The actual platform channel calls require the `flutter_callkeep` (or
/// equivalent) package. This class provides the interface and state management
/// so the rest of the app can be built and tested against it now.
abstract class CallKitService {
  /// Report an incoming call to the OS.
  ///
  /// On iOS this triggers the full-screen CallKit incoming-call UI.
  /// On Android it creates a ConnectionService connection and shows a
  /// high-priority notification.
  Future<void> reportIncomingCall({
    required String callId,
    required String callerNumber,
    String? callerName,
    bool hasVideo = false,
  });

  /// Notify the OS that a call has been answered and media is flowing.
  Future<void> reportCallStarted({
    required String callId,
  });

  /// Notify the OS that a call has ended.
  Future<void> reportCallEnded({
    required String callId,
  });

  /// Notify the OS that the call's hold state changed.
  Future<void> reportCallHeld({
    required String callId,
    required bool held,
  });

  /// Notify the OS that the call's mute state changed.
  Future<void> reportCallMuted({
    required String callId,
    required bool muted,
  });

  /// Register a callback for system-initiated call actions.
  ///
  /// The callback is invoked when the user answers/declines/holds from the
  /// system UI (lock screen, notification, CarPlay, Bluetooth headset, etc.).
  void setActionCallback(SystemCallActionCallback callback);

  /// Dispose of platform resources.
  void dispose();
}

// ---------------------------------------------------------------------------
// Default implementation
// ---------------------------------------------------------------------------

/// Default [CallKitService] implementation.
///
/// Wires platform channels for iOS CallKit / Android ConnectionService via the
/// callkeep package. Until that dependency is installed the actual platform
/// calls are stubbed with debug prints.
class DefaultCallKitService implements CallKitService {
  SystemCallActionCallback? _actionCallback;

  /// Track active calls reported to the OS.
  final Map<String, _ReportedCall> _activeCalls = {};

  @override
  Future<void> reportIncomingCall({
    required String callId,
    required String callerNumber,
    String? callerName,
    bool hasVideo = false,
  }) async {
    _activeCalls[callId] = _ReportedCall(
      callId: callId,
      callerNumber: callerNumber,
      callerName: callerName,
    );

    // TODO: FlutterCallkeep.displayIncomingCall(
    //   callId,
    //   callerNumber,
    //   callerName: callerName ?? callerNumber,
    //   hasVideo: hasVideo,
    //   handleType: 'number',
    // );

    debugPrint(
      '[CallKitService] Reported incoming call $callId '
      'from ${callerName ?? callerNumber}',
    );
  }

  @override
  Future<void> reportCallStarted({required String callId}) async {
    // TODO: FlutterCallkeep.reportConnectingOutgoingCallWithUUID(callId);
    // TODO: FlutterCallkeep.reportConnectedOutgoingCallWithUUID(callId);

    debugPrint('[CallKitService] Call started: $callId');
  }

  @override
  Future<void> reportCallEnded({required String callId}) async {
    _activeCalls.remove(callId);

    // TODO: FlutterCallkeep.endCall(callId);

    debugPrint('[CallKitService] Call ended: $callId');
  }

  @override
  Future<void> reportCallHeld({
    required String callId,
    required bool held,
  }) async {
    // TODO: FlutterCallkeep.setOnHold(callId, held);

    debugPrint(
      '[CallKitService] Call $callId hold=${held ? 'on' : 'off'}',
    );
  }

  @override
  Future<void> reportCallMuted({
    required String callId,
    required bool muted,
  }) async {
    // TODO: FlutterCallkeep.setMutedCall(callId, muted);

    debugPrint(
      '[CallKitService] Call $callId mute=${muted ? 'on' : 'off'}',
    );
  }

  @override
  void setActionCallback(SystemCallActionCallback callback) {
    _actionCallback = callback;

    // TODO: Register platform channel listeners:
    // FlutterCallkeep.addEventListener('answerCall', (event) {
    //   _actionCallback?.call(event['callUUID'], SystemCallAction.answer);
    // });
    // FlutterCallkeep.addEventListener('endCall', (event) {
    //   _actionCallback?.call(event['callUUID'], SystemCallAction.end);
    // });
    // FlutterCallkeep.addEventListener('setHeldCall', (event) {
    //   final held = event['hold'] as bool;
    //   _actionCallback?.call(
    //     event['callUUID'],
    //     held ? SystemCallAction.hold : SystemCallAction.unhold,
    //   );
    // });
    // FlutterCallkeep.addEventListener('setMutedCall', (event) {
    //   final muted = event['muted'] as bool;
    //   _actionCallback?.call(
    //     event['callUUID'],
    //     muted ? SystemCallAction.mute : SystemCallAction.unmute,
    //   );
    // });
  }

  /// Simulate a system call action (for testing / development).
  @visibleForTesting
  void simulateSystemAction(String callId, SystemCallAction action) {
    _actionCallback?.call(callId, action);
  }

  @override
  void dispose() {
    _activeCalls.clear();
    _actionCallback = null;
  }
}

// ---------------------------------------------------------------------------
// Internal tracking
// ---------------------------------------------------------------------------

class _ReportedCall {
  final String callId;
  final String callerNumber;
  final String? callerName;

  const _ReportedCall({
    required this.callId,
    required this.callerNumber,
    this.callerName,
  });
}
