import 'dart:async';

import 'package:flutter/foundation.dart';

// ---------------------------------------------------------------------------
// SIP registration and call state enums
// ---------------------------------------------------------------------------

/// Registration state of the SIP endpoint.
enum SipRegistrationState {
  unregistered,
  registering,
  registered,
  failed,
}

/// Current call direction.
enum CallDirection {
  incoming,
  outgoing,
}

/// State machine for an individual call leg.
enum SipCallState {
  idle,
  ringing,
  connecting,
  connected,
  held,
  ended,
}

// ---------------------------------------------------------------------------
// Data objects
// ---------------------------------------------------------------------------

/// SIP credentials needed to register with the PBX.
class SipCredentials {
  final String username;
  final String password;
  final String domain;
  final String wsUrl;

  /// Optional display name used in the From header.
  final String? displayName;

  const SipCredentials({
    required this.username,
    required this.password,
    required this.domain,
    required this.wsUrl,
    this.displayName,
  });
}

/// Describes the remote party of a call.
class CallPartyInfo {
  final String number;
  final String? displayName;

  const CallPartyInfo({
    required this.number,
    this.displayName,
  });

  /// Human-readable label: display name if available, otherwise the number.
  String get label => displayName ?? number;
}

/// Snapshot of the current call, emitted via [SipService.callStateStream].
class CallInfo {
  final String callId;
  final CallDirection direction;
  final SipCallState state;
  final CallPartyInfo remoteParty;
  final bool isMuted;
  final bool isOnHold;
  final DateTime? connectedAt;

  const CallInfo({
    required this.callId,
    required this.direction,
    required this.state,
    required this.remoteParty,
    this.isMuted = false,
    this.isOnHold = false,
    this.connectedAt,
  });

  CallInfo copyWith({
    String? callId,
    CallDirection? direction,
    SipCallState? state,
    CallPartyInfo? remoteParty,
    bool? isMuted,
    bool? isOnHold,
    DateTime? connectedAt,
  }) =>
      CallInfo(
        callId: callId ?? this.callId,
        direction: direction ?? this.direction,
        state: state ?? this.state,
        remoteParty: remoteParty ?? this.remoteParty,
        isMuted: isMuted ?? this.isMuted,
        isOnHold: isOnHold ?? this.isOnHold,
        connectedAt: connectedAt ?? this.connectedAt,
      );
}

// ---------------------------------------------------------------------------
// Abstract SIP service interface
// ---------------------------------------------------------------------------

/// Platform-agnostic interface for SIP/WebRTC call control.
///
/// Concrete implementations will use flutter_webrtc + a SIP-over-WebSocket
/// stack (e.g. sip_ua or a custom SIP parser) to drive actual media.
///
/// This abstract class is intentionally kept transport-agnostic so it can be
/// swapped for a mock in tests or replaced with a different RTC backend.
abstract class SipService {
  // ---- Registration --------------------------------------------------------

  /// Register with the PBX using the given SIP credentials.
  Future<void> register(SipCredentials credentials);

  /// Unregister and tear down the WebSocket transport.
  Future<void> unregister();

  /// Current registration state.
  SipRegistrationState get registrationState;

  /// Stream of registration state changes.
  Stream<SipRegistrationState> get registrationStateStream;

  // ---- Outbound call -------------------------------------------------------

  /// Originate a call to [number].
  ///
  /// Returns the call-id of the new session.
  Future<String> makeCall(String number);

  // ---- In-call controls ----------------------------------------------------

  /// Answer the current incoming call.
  Future<void> answer();

  /// Hang up the current (or specified) call.
  Future<void> hangup({String? callId});

  /// Place the active call on hold.
  Future<void> hold();

  /// Take the call off hold.
  Future<void> unhold();

  /// Mute the local microphone.
  Future<void> mute();

  /// Unmute the local microphone.
  Future<void> unmute();

  /// Send a DTMF digit (0-9, *, #).
  Future<void> sendDtmf(String digit);

  /// Blind transfer the current call to [target].
  Future<void> transfer(String target);

  // ---- Call state ----------------------------------------------------------

  /// Current call info, or null if no active call.
  CallInfo? get currentCall;

  /// Stream of call state changes.
  Stream<CallInfo?> get callStateStream;

  /// Dispose of resources.
  void dispose();
}

// ---------------------------------------------------------------------------
// Default (WebRTC) implementation
// ---------------------------------------------------------------------------

/// WebRTC-based SIP service that communicates with FreeSWITCH over WebSocket.
///
/// Requires `flutter_webrtc` and a SIP-over-WS implementation to be wired in.
/// For now this implementation contains the full state machine and callback
/// plumbing so that UI code can be built and tested against it. The actual
/// WebSocket/WebRTC calls are stubbed with TODOs that will be filled in once
/// the dependencies are added to pubspec.yaml.
class WebRtcSipService implements SipService {
  SipCredentials? _credentials;

  SipRegistrationState _registrationState = SipRegistrationState.unregistered;
  final _registrationController =
      StreamController<SipRegistrationState>.broadcast();

  CallInfo? _currentCall;
  final _callStateController = StreamController<CallInfo?>.broadcast();

  // ---- Registration --------------------------------------------------------

  @override
  SipRegistrationState get registrationState => _registrationState;

  @override
  Stream<SipRegistrationState> get registrationStateStream =>
      _registrationController.stream;

  @override
  Future<void> register(SipCredentials credentials) async {
    _credentials = credentials;
    _setRegistrationState(SipRegistrationState.registering);

    try {
      // TODO: Open WebSocket to credentials.wsUrl
      // TODO: Send SIP REGISTER via WebSocket transport
      // TODO: Set up ICE servers / STUN / TURN from config
      // TODO: Create RTCPeerConnection for media

      debugPrint(
        '[SipService] Registering ${credentials.username}@${credentials.domain} '
        'via ${credentials.wsUrl}',
      );

      // Simulate successful registration for now
      _setRegistrationState(SipRegistrationState.registered);
    } catch (e) {
      debugPrint('[SipService] Registration failed: $e');
      _setRegistrationState(SipRegistrationState.failed);
      rethrow;
    }
  }

  @override
  Future<void> unregister() async {
    // TODO: Send SIP un-REGISTER
    // TODO: Close WebSocket transport
    // TODO: Dispose RTCPeerConnection

    _credentials = null;
    _setRegistrationState(SipRegistrationState.unregistered);

    if (_currentCall != null) {
      await hangup();
    }
  }

  // ---- Outbound call -------------------------------------------------------

  @override
  Future<String> makeCall(String number) async {
    _assertRegistered();

    final callId = _generateCallId();

    final callInfo = CallInfo(
      callId: callId,
      direction: CallDirection.outgoing,
      state: SipCallState.connecting,
      remoteParty: CallPartyInfo(number: number),
    );

    _setCallState(callInfo);

    // TODO: Create SDP offer via RTCPeerConnection
    // TODO: Send SIP INVITE with SDP to number@domain
    // TODO: On 180 Ringing -> update state to ringing
    // TODO: On 200 OK -> setRemoteDescription, send ACK, update to connected

    debugPrint('[SipService] Making call to $number (callId: $callId)');

    return callId;
  }

  // ---- In-call controls ----------------------------------------------------

  @override
  Future<void> answer() async {
    final call = _currentCall;
    if (call == null || call.state != SipCallState.ringing) {
      throw StateError('No incoming call to answer');
    }

    // TODO: Create SDP answer via RTCPeerConnection
    // TODO: Send SIP 200 OK with SDP
    // TODO: Start media flow

    _setCallState(call.copyWith(
      state: SipCallState.connected,
      connectedAt: DateTime.now(),
    ));

    debugPrint('[SipService] Answered call ${call.callId}');
  }

  @override
  Future<void> hangup({String? callId}) async {
    final call = _currentCall;
    if (call == null) return;

    if (callId != null && call.callId != callId) return;

    // TODO: Send SIP BYE (or CANCEL if still ringing)
    // TODO: Close media tracks
    // TODO: Dispose RTCPeerConnection for this call

    _setCallState(call.copyWith(state: SipCallState.ended));

    // Clear the call after a short delay so the UI can show the ended state
    Future.delayed(const Duration(seconds: 2), () {
      if (_currentCall?.state == SipCallState.ended) {
        _setCallState(null);
      }
    });

    debugPrint('[SipService] Hung up call ${call.callId}');
  }

  @override
  Future<void> hold() async {
    final call = _currentCall;
    if (call == null || call.state != SipCallState.connected) return;

    // TODO: Send SIP re-INVITE with sendonly SDP

    _setCallState(call.copyWith(
      state: SipCallState.held,
      isOnHold: true,
    ));

    debugPrint('[SipService] Call ${call.callId} placed on hold');
  }

  @override
  Future<void> unhold() async {
    final call = _currentCall;
    if (call == null || call.state != SipCallState.held) return;

    // TODO: Send SIP re-INVITE with sendrecv SDP

    _setCallState(call.copyWith(
      state: SipCallState.connected,
      isOnHold: false,
    ));

    debugPrint('[SipService] Call ${call.callId} taken off hold');
  }

  @override
  Future<void> mute() async {
    final call = _currentCall;
    if (call == null) return;

    // TODO: Disable local audio track on RTCPeerConnection

    _setCallState(call.copyWith(isMuted: true));
    debugPrint('[SipService] Microphone muted');
  }

  @override
  Future<void> unmute() async {
    final call = _currentCall;
    if (call == null) return;

    // TODO: Enable local audio track on RTCPeerConnection

    _setCallState(call.copyWith(isMuted: false));
    debugPrint('[SipService] Microphone unmuted');
  }

  @override
  Future<void> sendDtmf(String digit) async {
    final call = _currentCall;
    if (call == null ||
        (call.state != SipCallState.connected &&
            call.state != SipCallState.held)) {
      return;
    }

    // TODO: Send SIP INFO with DTMF digit, or use RFC 4733 RTP events

    debugPrint('[SipService] Sent DTMF: $digit');
  }

  @override
  Future<void> transfer(String target) async {
    final call = _currentCall;
    if (call == null || call.state != SipCallState.connected) {
      throw StateError('No active call to transfer');
    }

    // TODO: Send SIP REFER to target

    debugPrint(
      '[SipService] Transferring call ${call.callId} to $target',
    );

    // After a successful REFER the call typically ends for us
    _setCallState(call.copyWith(state: SipCallState.ended));

    Future.delayed(const Duration(seconds: 2), () {
      if (_currentCall?.state == SipCallState.ended) {
        _setCallState(null);
      }
    });
  }

  // ---- Call state ----------------------------------------------------------

  @override
  CallInfo? get currentCall => _currentCall;

  @override
  Stream<CallInfo?> get callStateStream => _callStateController.stream;

  // ---- Incoming call simulation (called by the WS event handler) -----------

  /// Called when the WebSocket transport receives an incoming INVITE.
  void handleIncomingCall({
    required String callId,
    required String callerNumber,
    String? callerName,
  }) {
    final callInfo = CallInfo(
      callId: callId,
      direction: CallDirection.incoming,
      state: SipCallState.ringing,
      remoteParty: CallPartyInfo(
        number: callerNumber,
        displayName: callerName,
      ),
    );

    _setCallState(callInfo);
    debugPrint(
      '[SipService] Incoming call from $callerNumber (callId: $callId)',
    );
  }

  // ---- Disposal ------------------------------------------------------------

  @override
  void dispose() {
    _registrationController.close();
    _callStateController.close();
  }

  // ---- Private helpers -----------------------------------------------------

  void _setRegistrationState(SipRegistrationState newState) {
    _registrationState = newState;
    _registrationController.add(newState);
  }

  void _setCallState(CallInfo? callInfo) {
    _currentCall = callInfo;
    _callStateController.add(callInfo);
  }

  void _assertRegistered() {
    if (_registrationState != SipRegistrationState.registered) {
      throw StateError(
        'SIP service is not registered '
        '(current state: $_registrationState)',
      );
    }
  }

  int _callIdSeq = 0;

  String _generateCallId() {
    _callIdSeq++;
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    return 'np-$timestamp-$_callIdSeq';
  }
}
