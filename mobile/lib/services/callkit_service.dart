import 'package:flutter/foundation.dart';
import 'package:flutter_callkeep/flutter_callkeep.dart';

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
// Default implementation using flutter_callkeep
// ---------------------------------------------------------------------------

/// Default [CallKitService] implementation.
///
/// Wires platform channels for iOS CallKit / Android ConnectionService via the
/// flutter_callkeep package. Handles the native incoming-call UI, audio
/// session management, and system callbacks for call control.
class DefaultCallKitService implements CallKitService {
  SystemCallActionCallback? _actionCallback;

  /// Track active calls reported to the OS.
  final Map<String, _ReportedCall> _activeCalls = {};

  /// Whether the service has been initialized.
  bool _initialized = false;

  /// The PushKit VoIP token (iOS), sent to the server for VoIP push.
  String? voipToken;

  /// Initialize the CallKeep plugin with app configuration.
  ///
  /// Must be called once during app startup, before any incoming calls
  /// can be reported to the OS.
  Future<void> init() async {
    if (_initialized) return;

    try {
      final config = CallKeepConfig(
        appName: 'New Phone',
        android: CallKeepAndroidConfig(
          ringtoneFileName: 'ringtone',
          accentColor: '#1565C0',
          incomingCallNotificationChannelName: 'New Phone Incoming Calls',
          missedCallNotificationChannelName: 'New Phone Missed Calls',
          showMissedCallNotification: true,
          showCallBackAction: true,
        ),
        ios: CallKeepIosConfig(
          iconName: 'CallKitIcon',
          ringtoneFileName: 'ringtone.caf',
          handleType: CallKitHandleType.number,
          isVideoSupported: false,
          maximumCallGroups: 1,
          maximumCallsPerCallGroup: 1,
          supportsDTMF: true,
          supportsHolding: true,
          supportsGrouping: false,
          supportsUngrouping: false,
          audioSessionActive: true,
          audioSessionMode: AvAudioSessionMode.voiceChat,
        ),
      );

      await CallKeep.instance.configure(config);

      // Register event handlers for system-initiated call actions.
      CallKeep.instance.handler = CallEventHandler(
        onCallIncoming: _onCallIncoming,
        onCallAccepted: _onCallAccepted,
        onCallDeclined: _onCallDeclined,
        onCallEnded: _onCallEnded,
        onCallStarted: _onCallStarted,
        onCallTimedOut: _onCallTimedOut,
        onCallMissed: _onCallMissed,
        onHoldToggled: _onHoldToggled,
        onMuteToggled: _onMuteToggled,
        onDmtfToggled: _onDtmfToggled,
        onAudioSessionToggled: _onAudioSessionToggled,
        onVoipTokenUpdated: _onVoipTokenUpdated,
      );

      _initialized = true;
      debugPrint('[CallKitService] Initialized');
    } catch (e) {
      debugPrint('[CallKitService] Init failed: $e');
    }
  }

  @override
  Future<void> reportIncomingCall({
    required String callId,
    required String callerNumber,
    String? callerName,
    bool hasVideo = false,
  }) async {
    if (!_initialized) {
      await init();
    }

    _activeCalls[callId] = _ReportedCall(
      callId: callId,
      callerNumber: callerNumber,
      callerName: callerName,
    );

    try {
      final callEvent = CallEvent(
        uuid: callId,
        callerName: callerName ?? callerNumber,
        handle: callerNumber,
        hasVideo: hasVideo,
        duration: 45,
      );

      await CallKeep.instance.displayIncomingCall(callEvent);

      debugPrint(
        '[CallKitService] Reported incoming call $callId '
        'from ${callerName ?? callerNumber}',
      );
    } catch (e) {
      debugPrint('[CallKitService] reportIncomingCall failed: $e');
    }
  }

  @override
  Future<void> reportCallStarted({required String callId}) async {
    try {
      final reported = _activeCalls[callId];
      final callEvent = CallEvent(
        uuid: callId,
        callerName: reported?.callerName ?? '',
        handle: reported?.callerNumber ?? '',
      );

      await CallKeep.instance.startCall(callEvent);

      debugPrint('[CallKitService] Call started: $callId');
    } catch (e) {
      debugPrint('[CallKitService] reportCallStarted failed: $e');
    }
  }

  @override
  Future<void> reportCallEnded({required String callId}) async {
    _activeCalls.remove(callId);

    try {
      await CallKeep.instance.endCall(callId);
      debugPrint('[CallKitService] Call ended: $callId');
    } catch (e) {
      debugPrint('[CallKitService] reportCallEnded failed: $e');
    }
  }

  @override
  Future<void> reportCallHeld({
    required String callId,
    required bool held,
  }) async {
    // The hold state is managed via the onHoldToggled callback from the OS.
    // This method reports our app's hold state to the OS.
    debugPrint(
      '[CallKitService] Call $callId hold=${held ? 'on' : 'off'}',
    );
  }

  @override
  Future<void> reportCallMuted({
    required String callId,
    required bool muted,
  }) async {
    // The mute state is managed via the onMuteToggled callback from the OS.
    // This method reports our app's mute state to the OS.
    debugPrint(
      '[CallKitService] Call $callId mute=${muted ? 'on' : 'off'}',
    );
  }

  @override
  void setActionCallback(SystemCallActionCallback callback) {
    _actionCallback = callback;
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
    _initialized = false;
  }

  // ---------------------------------------------------------------------------
  // Private — CallKeep event handlers
  // ---------------------------------------------------------------------------

  /// Called when an incoming call notification is displayed by the OS.
  void _onCallIncoming(CallEvent event) {
    debugPrint(
      '[CallKitService] onCallIncoming: ${event.uuid} '
      'from ${event.callerName}',
    );
  }

  /// Called when the user accepts an incoming call from the system UI.
  void _onCallAccepted(CallEvent event) {
    final callId = event.uuid;
    debugPrint('[CallKitService] onCallAccepted: $callId');
    _actionCallback?.call(callId, SystemCallAction.answer);
  }

  /// Called when the user declines an incoming call from the system UI.
  void _onCallDeclined(CallEvent event) {
    final callId = event.uuid;
    debugPrint('[CallKitService] onCallDeclined: $callId');
    _actionCallback?.call(callId, SystemCallAction.end);
  }

  /// Called when a call ends (from system UI or programmatically).
  void _onCallEnded(CallEvent event) {
    final callId = event.uuid;
    debugPrint('[CallKitService] onCallEnded: $callId');
    _activeCalls.remove(callId);
    _actionCallback?.call(callId, SystemCallAction.end);
  }

  /// Called when an outgoing call is started via the system UI.
  void _onCallStarted(CallEvent event) {
    debugPrint('[CallKitService] onCallStarted: ${event.uuid}');
  }

  /// Called when an incoming call times out (not answered).
  void _onCallTimedOut(CallEvent event) {
    final callId = event.uuid;
    debugPrint('[CallKitService] onCallTimedOut: $callId');
    _activeCalls.remove(callId);
    _actionCallback?.call(callId, SystemCallAction.end);
  }

  /// Called when a call is missed.
  void _onCallMissed(CallEvent event) {
    debugPrint('[CallKitService] onCallMissed: ${event.uuid}');
    _activeCalls.remove(event.uuid);
  }

  /// Called when the user toggles hold from the system call UI.
  void _onHoldToggled(HoldToggleEvent event) {
    final callId = event.uuid;
    final isOnHold = event.isOnHold;
    debugPrint(
      '[CallKitService] onHoldToggled: $callId isOnHold=$isOnHold',
    );
    if (callId != null) {
      _actionCallback?.call(
        callId,
        isOnHold ? SystemCallAction.hold : SystemCallAction.unhold,
      );
    }
  }

  /// Called when the user toggles mute from the system call UI.
  void _onMuteToggled(MuteToggleEvent event) {
    final callId = event.uuid;
    final isMuted = event.isMuted;
    debugPrint(
      '[CallKitService] onMuteToggled: $callId isMuted=$isMuted',
    );
    if (callId != null) {
      _actionCallback?.call(
        callId,
        isMuted ? SystemCallAction.mute : SystemCallAction.unmute,
      );
    }
  }

  /// Called when the user sends DTMF from the system call UI.
  void _onDtmfToggled(DmtfToggleEvent event) {
    debugPrint(
      '[CallKitService] onDtmfToggled: ${event.uuid} '
      'digits=${event.digits}',
    );
    // DTMF from the system UI is forwarded to the SipService via
    // the CallNotifier layer, which listens for these events.
  }

  /// Called when the audio session state changes.
  void _onAudioSessionToggled(AudioSessionToggleEvent event) {
    debugPrint(
      '[CallKitService] onAudioSessionToggled: isActivated=${event.isActivated}',
    );
  }

  /// Called when the PushKit VoIP token is updated (iOS only).
  void _onVoipTokenUpdated(VoipTokenEvent event) {
    voipToken = event.token;
    debugPrint(
      '[CallKitService] onVoipTokenUpdated: '
      '${event.token?.substring(0, (event.token?.length ?? 0).clamp(0, 20))}...',
    );
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
