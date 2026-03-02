import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/sip_service.dart';
import '../services/callkit_service.dart';
import '../services/audio_service.dart';

// ---------------------------------------------------------------------------
// Call state
// ---------------------------------------------------------------------------

/// High-level call state consumed by the UI.
sealed class CallState {
  const CallState();
}

/// No active call.
class CallIdle extends CallState {
  const CallIdle();
}

/// An incoming call is ringing.
class CallRinging extends CallState {
  final String callId;
  final CallPartyInfo remoteParty;

  const CallRinging({
    required this.callId,
    required this.remoteParty,
  });
}

/// An outgoing call is connecting (ringing at the far end).
class CallConnecting extends CallState {
  final String callId;
  final CallPartyInfo remoteParty;

  const CallConnecting({
    required this.callId,
    required this.remoteParty,
  });
}

/// A call is active (connected or on hold).
class CallConnected extends CallState {
  final String callId;
  final CallPartyInfo remoteParty;
  final Duration duration;
  final bool isMuted;
  final bool isOnHold;
  final bool isSpeaker;
  final AudioRoute audioRoute;

  const CallConnected({
    required this.callId,
    required this.remoteParty,
    required this.duration,
    this.isMuted = false,
    this.isOnHold = false,
    this.isSpeaker = false,
    this.audioRoute = AudioRoute.earpiece,
  });

  CallConnected copyWith({
    String? callId,
    CallPartyInfo? remoteParty,
    Duration? duration,
    bool? isMuted,
    bool? isOnHold,
    bool? isSpeaker,
    AudioRoute? audioRoute,
  }) =>
      CallConnected(
        callId: callId ?? this.callId,
        remoteParty: remoteParty ?? this.remoteParty,
        duration: duration ?? this.duration,
        isMuted: isMuted ?? this.isMuted,
        isOnHold: isOnHold ?? this.isOnHold,
        isSpeaker: isSpeaker ?? this.isSpeaker,
        audioRoute: audioRoute ?? this.audioRoute,
      );
}

/// The call has ended.
class CallEnded extends CallState {
  final String callId;
  final CallPartyInfo remoteParty;
  final Duration totalDuration;

  const CallEnded({
    required this.callId,
    required this.remoteParty,
    required this.totalDuration,
  });
}

// ---------------------------------------------------------------------------
// Service providers
// ---------------------------------------------------------------------------

/// SIP service singleton provider.
final sipServiceProvider = Provider<SipService>((ref) {
  final service = WebRtcSipService();
  ref.onDispose(() => service.dispose());
  return service;
});

/// CallKit service singleton provider.
final callKitServiceProvider = Provider<CallKitService>((ref) {
  final service = DefaultCallKitService();
  ref.onDispose(() => service.dispose());
  return service;
});

/// Audio service singleton provider.
final audioServiceProvider = Provider<AudioService>((ref) {
  final service = DefaultAudioService();
  ref.onDispose(() => service.dispose());
  return service;
});

// ---------------------------------------------------------------------------
// Call state provider
// ---------------------------------------------------------------------------

/// Main call state notifier — single source of truth for the active call.
final callProvider = StateNotifierProvider<CallNotifier, CallState>((ref) {
  final sipService = ref.watch(sipServiceProvider);
  final callKitService = ref.watch(callKitServiceProvider);
  final audioService = ref.watch(audioServiceProvider);

  return CallNotifier(
    sipService: sipService,
    callKitService: callKitService,
    audioService: audioService,
  );
});

class CallNotifier extends StateNotifier<CallState> {
  final SipService _sipService;
  final CallKitService _callKitService;
  final AudioService _audioService;

  StreamSubscription<CallInfo?>? _callStateSub;
  StreamSubscription<AudioRoute>? _audioRouteSub;
  Timer? _durationTimer;
  DateTime? _connectedAt;

  CallNotifier({
    required SipService sipService,
    required CallKitService callKitService,
    required AudioService audioService,
  })  : _sipService = sipService,
        _callKitService = callKitService,
        _audioService = audioService,
        super(const CallIdle()) {
    _listenToCallState();
    _listenToAudioRoute();
    _listenToSystemActions();
  }

  // ---- Public actions (called from UI) -------------------------------------

  /// Originate an outgoing call to [number].
  Future<void> makeCall(String number) async {
    if (state is! CallIdle) {
      debugPrint('[CallProvider] Cannot make call — not idle');
      return;
    }

    try {
      await _sipService.makeCall(number);
    } catch (e) {
      debugPrint('[CallProvider] makeCall failed: $e');
    }
  }

  /// Answer the current incoming call.
  Future<void> answer() async {
    if (state is! CallRinging) return;

    try {
      await _sipService.answer();
      final callId = (state as CallRinging).callId;
      await _callKitService.reportCallStarted(callId: callId);
    } catch (e) {
      debugPrint('[CallProvider] answer failed: $e');
    }
  }

  /// Hang up the current call.
  Future<void> hangup() async {
    final currentState = state;
    String? callId;

    if (currentState is CallRinging) {
      callId = currentState.callId;
    } else if (currentState is CallConnecting) {
      callId = currentState.callId;
    } else if (currentState is CallConnected) {
      callId = currentState.callId;
    } else {
      return;
    }

    try {
      await _sipService.hangup(callId: callId);
      if (callId != null) {
        await _callKitService.reportCallEnded(callId: callId);
      }
    } catch (e) {
      debugPrint('[CallProvider] hangup failed: $e');
    }
  }

  /// Toggle mute state.
  Future<void> toggleMute() async {
    final currentState = state;
    if (currentState is! CallConnected) return;

    try {
      if (currentState.isMuted) {
        await _sipService.unmute();
      } else {
        await _sipService.mute();
      }
      await _callKitService.reportCallMuted(
        callId: currentState.callId,
        muted: !currentState.isMuted,
      );
    } catch (e) {
      debugPrint('[CallProvider] toggleMute failed: $e');
    }
  }

  /// Toggle hold state.
  Future<void> toggleHold() async {
    final currentState = state;
    if (currentState is! CallConnected) return;

    try {
      if (currentState.isOnHold) {
        await _sipService.unhold();
      } else {
        await _sipService.hold();
      }
      await _callKitService.reportCallHeld(
        callId: currentState.callId,
        held: !currentState.isOnHold,
      );
    } catch (e) {
      debugPrint('[CallProvider] toggleHold failed: $e');
    }
  }

  /// Toggle speaker output.
  Future<void> toggleSpeaker() async {
    final currentState = state;
    if (currentState is! CallConnected) return;

    try {
      if (currentState.isSpeaker) {
        await _audioService.setAudioRoute(AudioRoute.earpiece);
      } else {
        await _audioService.setAudioRoute(AudioRoute.speaker);
      }
    } catch (e) {
      debugPrint('[CallProvider] toggleSpeaker failed: $e');
    }
  }

  /// Send a DTMF digit during an active call.
  Future<void> sendDtmf(String digit) async {
    if (state is! CallConnected) return;

    try {
      await _sipService.sendDtmf(digit);
    } catch (e) {
      debugPrint('[CallProvider] sendDtmf failed: $e');
    }
  }

  /// Transfer the active call to [target].
  Future<void> transfer(String target) async {
    if (state is! CallConnected) return;

    try {
      await _sipService.transfer(target);
    } catch (e) {
      debugPrint('[CallProvider] transfer failed: $e');
    }
  }

  // ---- Private listeners ---------------------------------------------------

  void _listenToCallState() {
    _callStateSub = _sipService.callStateStream.listen((callInfo) {
      if (callInfo == null) {
        _stopDurationTimer();
        state = const CallIdle();
        return;
      }

      switch (callInfo.state) {
        case SipCallState.idle:
          _stopDurationTimer();
          state = const CallIdle();

        case SipCallState.ringing:
          if (callInfo.direction == CallDirection.incoming) {
            state = CallRinging(
              callId: callInfo.callId,
              remoteParty: callInfo.remoteParty,
            );
            // Report incoming call to the OS for lock-screen UI
            _callKitService.reportIncomingCall(
              callId: callInfo.callId,
              callerNumber: callInfo.remoteParty.number,
              callerName: callInfo.remoteParty.displayName,
            );
          } else {
            state = CallConnecting(
              callId: callInfo.callId,
              remoteParty: callInfo.remoteParty,
            );
          }

        case SipCallState.connecting:
          state = CallConnecting(
            callId: callInfo.callId,
            remoteParty: callInfo.remoteParty,
          );

        case SipCallState.connected:
          _connectedAt = callInfo.connectedAt ?? DateTime.now();
          _startDurationTimer(callInfo);

        case SipCallState.held:
          _updateConnectedState(callInfo);

        case SipCallState.ended:
          _stopDurationTimer();
          final duration = _connectedAt != null
              ? DateTime.now().difference(_connectedAt!)
              : Duration.zero;

          state = CallEnded(
            callId: callInfo.callId,
            remoteParty: callInfo.remoteParty,
            totalDuration: duration,
          );
          _connectedAt = null;
      }
    });
  }

  void _listenToAudioRoute() {
    _audioRouteSub = _audioService.audioRouteStream.listen((route) {
      final currentState = state;
      if (currentState is CallConnected) {
        state = currentState.copyWith(
          audioRoute: route,
          isSpeaker: route == AudioRoute.speaker,
        );
      }
    });
  }

  void _listenToSystemActions() {
    _callKitService.setActionCallback((callId, action) {
      switch (action) {
        case SystemCallAction.answer:
          answer();
        case SystemCallAction.end:
          hangup();
        case SystemCallAction.hold:
        case SystemCallAction.unhold:
          toggleHold();
        case SystemCallAction.mute:
        case SystemCallAction.unmute:
          toggleMute();
      }
    });
  }

  void _startDurationTimer(CallInfo callInfo) {
    _stopDurationTimer();
    _updateConnectedState(callInfo);

    _durationTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      final sipCall = _sipService.currentCall;
      if (sipCall != null &&
          (sipCall.state == SipCallState.connected ||
              sipCall.state == SipCallState.held)) {
        _updateConnectedState(sipCall);
      }
    });
  }

  void _updateConnectedState(CallInfo callInfo) {
    final duration = _connectedAt != null
        ? DateTime.now().difference(_connectedAt!)
        : Duration.zero;

    state = CallConnected(
      callId: callInfo.callId,
      remoteParty: callInfo.remoteParty,
      duration: duration,
      isMuted: callInfo.isMuted,
      isOnHold: callInfo.isOnHold,
      isSpeaker: _audioService.currentRoute == AudioRoute.speaker,
      audioRoute: _audioService.currentRoute,
    );
  }

  void _stopDurationTimer() {
    _durationTimer?.cancel();
    _durationTimer = null;
  }

  @override
  void dispose() {
    _callStateSub?.cancel();
    _audioRouteSub?.cancel();
    _stopDurationTimer();
    super.dispose();
  }
}
