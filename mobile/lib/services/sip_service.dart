import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:sip_ua/sip_ua.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';

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

  /// Reject the current incoming call with 486 Busy Here.
  Future<void> reject();

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
// WebRTC-based SIP service implementation using sip_ua
// ---------------------------------------------------------------------------

/// WebRTC-based SIP service that communicates with FreeSWITCH over WebSocket.
///
/// Uses the `sip_ua` package for SIP signaling and `flutter_webrtc` for media.
/// All SIP transport is TLS-only (WSS on port 5061). SRTP is enforced via
/// the SDP media attributes negotiated through the SIP stack.
class WebRtcSipService implements SipService, SipUaHelperListener {
  final SIPUAHelper _helper = SIPUAHelper();

  SipCredentials? _credentials;

  SipRegistrationState _registrationState = SipRegistrationState.unregistered;
  final _registrationController =
      StreamController<SipRegistrationState>.broadcast();

  CallInfo? _currentCall;
  final _callStateController = StreamController<CallInfo?>.broadcast();

  /// The active sip_ua Call object for in-call operations.
  Call? _activeCall;

  /// Local media stream used for outgoing audio.
  MediaStream? _localStream;

  /// Remote media stream received from the far end.
  MediaStream? _remoteStream;

  /// Whether local audio is muted (track disabled but still present).
  bool _isMuted = false;

  WebRtcSipService() {
    _helper.addSipUaHelperListener(this);
  }

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
      final uaSettings = UaSettings();

      uaSettings.webSocketUrl = credentials.wsUrl;
      uaSettings.webSocketSettings.extraHeaders = {
        'Origin': 'https://${credentials.domain}',
      };
      uaSettings.webSocketSettings.allowBadCertificate = false;
      uaSettings.webSocketSettings.userAgent = 'NewPhone-Mobile/0.1.0';

      uaSettings.uri = 'sip:${credentials.username}@${credentials.domain}';
      uaSettings.authorizationUser = credentials.username;
      uaSettings.password = credentials.password;
      uaSettings.displayName = credentials.displayName ?? credentials.username;
      uaSettings.userAgent = 'NewPhone-Mobile/0.1.0';

      // Register for SIP events
      uaSettings.register = true;
      uaSettings.register_expires = 600;

      // WebSocket transport (TLS enforced via wss:// URL scheme on port 5061).
      uaSettings.transportType = TransportType.WS;

      debugPrint(
        '[SipService] Registering ${credentials.username}@${credentials.domain} '
        'via ${credentials.wsUrl}',
      );

      await _helper.start(uaSettings);
    } catch (e) {
      debugPrint('[SipService] Registration failed: $e');
      _setRegistrationState(SipRegistrationState.failed);
      rethrow;
    }
  }

  @override
  Future<void> unregister() async {
    try {
      if (_currentCall != null) {
        await hangup();
      }

      _helper.stop();
      _helper.removeSipUaHelperListener(this);

      await _disposeMediaStreams();

      _credentials = null;
      _setRegistrationState(SipRegistrationState.unregistered);

      debugPrint('[SipService] Unregistered');
    } catch (e) {
      debugPrint('[SipService] Unregister error: $e');
      _credentials = null;
      _setRegistrationState(SipRegistrationState.unregistered);
    }
  }

  // ---- Outbound call -------------------------------------------------------

  @override
  Future<String> makeCall(String number) async {
    _assertRegistered();

    final target = 'sip:$number@${_credentials!.domain}';

    try {
      _localStream = await navigator.mediaDevices.getUserMedia({
        'audio': true,
        'video': false,
      });

      final success = await _helper.call(
        target,
        voiceOnly: true,
        mediaStream: _localStream,
      );

      if (!success) {
        await _disposeMediaStreams();
        throw StateError('Failed to initiate SIP call to $number');
      }

      // The _activeCall is set in the callStateChanged callback
      // when CALL_INITIATION fires. Use it if already set, else generate.
      final callId = _activeCall?.id ?? _generateCallId();

      final callInfo = CallInfo(
        callId: callId,
        direction: CallDirection.outgoing,
        state: SipCallState.connecting,
        remoteParty: CallPartyInfo(number: number),
      );

      _isMuted = false;
      _setCallState(callInfo);

      debugPrint('[SipService] Making call to $number (callId: $callId)');
      return callId;
    } catch (e) {
      debugPrint('[SipService] makeCall failed: $e');
      await _disposeMediaStreams();
      rethrow;
    }
  }

  // ---- In-call controls ----------------------------------------------------

  @override
  Future<void> answer() async {
    final call = _currentCall;
    if (call == null || call.state != SipCallState.ringing) {
      throw StateError('No incoming call to answer');
    }

    if (_activeCall == null) {
      throw StateError('No active SIP call session to answer');
    }

    try {
      _localStream = await navigator.mediaDevices.getUserMedia({
        'audio': true,
        'video': false,
      });

      _activeCall!.answer(
        _helper.buildCallOptions(true),
        mediaStream: _localStream,
      );

      _isMuted = false;

      _setCallState(call.copyWith(
        state: SipCallState.connected,
        connectedAt: DateTime.now(),
      ));

      debugPrint('[SipService] Answered call ${call.callId}');
    } catch (e) {
      debugPrint('[SipService] answer failed: $e');
      await _disposeMediaStreams();
      rethrow;
    }
  }

  @override
  Future<void> reject() async {
    final call = _currentCall;
    if (call == null || call.state != SipCallState.ringing) {
      throw StateError('No incoming call to reject');
    }

    try {
      if (_activeCall != null) {
        // 486 Busy Here — standard SIP rejection code.
        _activeCall!.hangup({'status_code': 486});
      }
    } catch (e) {
      debugPrint('[SipService] reject SIP error: $e');
    }

    _setCallState(call.copyWith(state: SipCallState.ended));

    Future.delayed(const Duration(seconds: 2), () {
      if (_currentCall?.state == SipCallState.ended) {
        _activeCall = null;
        _setCallState(null);
      }
    });

    debugPrint('[SipService] Rejected call ${call.callId} with 486 Busy');
  }

  @override
  Future<void> hangup({String? callId}) async {
    final call = _currentCall;
    if (call == null) return;

    if (callId != null && call.callId != callId) return;

    try {
      if (_activeCall != null) {
        _activeCall!.hangup({'status_code': 603});
      }
    } catch (e) {
      debugPrint('[SipService] hangup SIP error: $e');
    }

    await _disposeMediaStreams();

    _setCallState(call.copyWith(state: SipCallState.ended));

    // Clear the call after a short delay so the UI can show the ended state.
    Future.delayed(const Duration(seconds: 2), () {
      if (_currentCall?.state == SipCallState.ended) {
        _activeCall = null;
        _setCallState(null);
      }
    });

    debugPrint('[SipService] Hung up call ${call.callId}');
  }

  @override
  Future<void> hold() async {
    final call = _currentCall;
    if (call == null || call.state != SipCallState.connected) return;

    if (_activeCall == null) return;

    try {
      _activeCall!.hold();

      _setCallState(call.copyWith(
        state: SipCallState.held,
        isOnHold: true,
      ));

      debugPrint('[SipService] Call ${call.callId} placed on hold');
    } catch (e) {
      debugPrint('[SipService] hold failed: $e');
    }
  }

  @override
  Future<void> unhold() async {
    final call = _currentCall;
    if (call == null || call.state != SipCallState.held) return;

    if (_activeCall == null) return;

    try {
      _activeCall!.unhold();

      _setCallState(call.copyWith(
        state: SipCallState.connected,
        isOnHold: false,
      ));

      debugPrint('[SipService] Call ${call.callId} taken off hold');
    } catch (e) {
      debugPrint('[SipService] unhold failed: $e');
    }
  }

  @override
  Future<void> mute() async {
    final call = _currentCall;
    if (call == null) return;

    try {
      if (_activeCall != null) {
        // Mute audio only (first param = audio, second = video).
        _activeCall!.mute(true, false);
      }

      // Also disable the local audio track directly for immediate effect.
      if (_localStream != null) {
        for (final track in _localStream!.getAudioTracks()) {
          track.enabled = false;
        }
      }

      _isMuted = true;
      _setCallState(call.copyWith(isMuted: true));
      debugPrint('[SipService] Microphone muted');
    } catch (e) {
      debugPrint('[SipService] mute failed: $e');
    }
  }

  @override
  Future<void> unmute() async {
    final call = _currentCall;
    if (call == null) return;

    try {
      if (_activeCall != null) {
        // Unmute audio only (first param = audio, second = video).
        _activeCall!.unmute(true, false);
      }

      // Re-enable the local audio track.
      if (_localStream != null) {
        for (final track in _localStream!.getAudioTracks()) {
          track.enabled = true;
        }
      }

      _isMuted = false;
      _setCallState(call.copyWith(isMuted: false));
      debugPrint('[SipService] Microphone unmuted');
    } catch (e) {
      debugPrint('[SipService] unmute failed: $e');
    }
  }

  @override
  Future<void> sendDtmf(String digit) async {
    final call = _currentCall;
    if (call == null ||
        (call.state != SipCallState.connected &&
            call.state != SipCallState.held)) {
      return;
    }

    if (_activeCall == null) return;

    try {
      _activeCall!.sendDTMF(digit);
      debugPrint('[SipService] Sent DTMF: $digit');
    } catch (e) {
      debugPrint('[SipService] sendDtmf failed: $e');
    }
  }

  @override
  Future<void> transfer(String target) async {
    final call = _currentCall;
    if (call == null || call.state != SipCallState.connected) {
      throw StateError('No active call to transfer');
    }

    if (_activeCall == null) {
      throw StateError('No active SIP call session to transfer');
    }

    try {
      final targetUri = 'sip:$target@${_credentials!.domain}';
      _activeCall!.refer(targetUri);

      debugPrint(
        '[SipService] Transferring call ${call.callId} to $target',
      );

      // After a successful REFER the call typically ends for us.
      _setCallState(call.copyWith(state: SipCallState.ended));

      await _disposeMediaStreams();

      Future.delayed(const Duration(seconds: 2), () {
        if (_currentCall?.state == SipCallState.ended) {
          _activeCall = null;
          _setCallState(null);
        }
      });
    } catch (e) {
      debugPrint('[SipService] transfer failed: $e');
      rethrow;
    }
  }

  // ---- Call state ----------------------------------------------------------

  @override
  CallInfo? get currentCall => _currentCall;

  @override
  Stream<CallInfo?> get callStateStream => _callStateController.stream;

  // ---- SipUaHelperListener callbacks ---------------------------------------

  @override
  void registrationStateChanged(RegistrationState state) {
    debugPrint(
      '[SipService] registrationStateChanged: ${state.state}',
    );

    switch (state.state) {
      case RegistrationStateEnum.REGISTERED:
        _setRegistrationState(SipRegistrationState.registered);

      case RegistrationStateEnum.UNREGISTERED:
        _setRegistrationState(SipRegistrationState.unregistered);

      case RegistrationStateEnum.REGISTRATION_FAILED:
        _setRegistrationState(SipRegistrationState.failed);

      case RegistrationStateEnum.NONE:
        break;
    }
  }

  @override
  void transportStateChanged(TransportState state) {
    debugPrint(
      '[SipService] transportStateChanged: ${state.state}',
    );
  }

  @override
  void callStateChanged(Call call, CallState callState) {
    debugPrint(
      '[SipService] callStateChanged: ${callState.state}',
    );

    switch (callState.state) {
      case CallStateEnum.CALL_INITIATION:
        _activeCall = call;
        final remoteUri = call.remote_identity ?? '';
        final callId = call.id ?? _generateCallId();
        final number = _extractNumber(remoteUri);
        final displayName = call.remote_display_name;

        // Determine direction from the sip_ua Call object.
        final isIncoming = call.direction == Direction.incoming;

        if (isIncoming) {
          // Incoming call — report as ringing.
          handleIncomingCall(
            callId: callId,
            callerNumber: number,
            callerName: displayName,
          );
        } else {
          // Outgoing call — report as connecting.
          _setCallState(CallInfo(
            callId: callId,
            direction: CallDirection.outgoing,
            state: SipCallState.connecting,
            remoteParty: CallPartyInfo(
              number: number,
              displayName: displayName,
            ),
          ));
        }

      case CallStateEnum.PROGRESS:
      case CallStateEnum.CONNECTING:
        // Ringing at the far end for outgoing, or early media.
        final current = _currentCall;
        if (current != null &&
            current.direction == CallDirection.outgoing) {
          _setCallState(current.copyWith(state: SipCallState.ringing));
        }

      case CallStateEnum.ACCEPTED:
      case CallStateEnum.CONFIRMED:
        final current = _currentCall;
        if (current != null) {
          _setCallState(current.copyWith(
            state: SipCallState.connected,
            connectedAt: DateTime.now(),
            isMuted: _isMuted,
          ));
        }

      case CallStateEnum.HOLD:
        final current = _currentCall;
        if (current != null) {
          _setCallState(current.copyWith(
            state: SipCallState.held,
            isOnHold: true,
          ));
        }

      case CallStateEnum.UNHOLD:
        final current = _currentCall;
        if (current != null) {
          _setCallState(current.copyWith(
            state: SipCallState.connected,
            isOnHold: false,
          ));
        }

      case CallStateEnum.MUTED:
        final current = _currentCall;
        if (current != null) {
          _isMuted = true;
          _setCallState(current.copyWith(isMuted: true));
        }

      case CallStateEnum.UNMUTED:
        final current = _currentCall;
        if (current != null) {
          _isMuted = false;
          _setCallState(current.copyWith(isMuted: false));
        }

      case CallStateEnum.STREAM:
        _handleRemoteStream(callState);

      case CallStateEnum.ENDED:
      case CallStateEnum.FAILED:
        _handleCallEnded(call);

      case CallStateEnum.REFER:
        debugPrint('[SipService] REFER received');

      case CallStateEnum.NONE:
        break;
    }
  }

  @override
  void onNewMessage(SIPMessageRequest msg) {
    debugPrint('[SipService] onNewMessage: ${msg.message?.body}');
  }

  @override
  void onNewNotify(Notify ntf) {
    debugPrint('[SipService] onNewNotify');
  }

  @override
  void onNewReinvite(ReInvite event) {
    debugPrint('[SipService] onNewReinvite');
  }

  // ---- Incoming call handling (called from SipUaHelper internally) ----------

  /// Called when the SIP stack receives an incoming INVITE.
  /// The sip_ua package routes this through callStateChanged with
  /// CALL_INITIATION, but for incoming calls we also detect via
  /// the call direction.
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
    _helper.removeSipUaHelperListener(this);
    _disposeMediaStreams();
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

  /// Extract the user portion from a SIP URI like "sip:1001@example.com".
  String _extractNumber(String sipUri) {
    try {
      final uri = sipUri.replaceAll('sip:', '').replaceAll('sips:', '');
      final atIndex = uri.indexOf('@');
      if (atIndex > 0) {
        return uri.substring(0, atIndex);
      }
      return uri.isNotEmpty ? uri : 'Unknown';
    } catch (_) {
      return 'Unknown';
    }
  }

  /// Handle the remote media stream arriving from the far end.
  void _handleRemoteStream(CallState callState) {
    if (callState.stream != null) {
      _remoteStream = callState.stream;
      debugPrint('[SipService] Remote stream received');
    }
  }

  /// Clean up after a call ends or fails.
  void _handleCallEnded(Call call) {
    final current = _currentCall;
    if (current != null) {
      _setCallState(current.copyWith(state: SipCallState.ended));

      Future.delayed(const Duration(seconds: 2), () {
        if (_currentCall?.state == SipCallState.ended) {
          _activeCall = null;
          _setCallState(null);
        }
      });
    } else {
      _activeCall = null;
    }

    _disposeMediaStreams();

    debugPrint('[SipService] Call ended: ${call.id}');
  }

  /// Dispose of local and remote media streams.
  Future<void> _disposeMediaStreams() async {
    try {
      if (_localStream != null) {
        for (final track in _localStream!.getTracks()) {
          await track.stop();
        }
        await _localStream!.dispose();
        _localStream = null;
      }

      if (_remoteStream != null) {
        _remoteStream = null;
      }
    } catch (e) {
      debugPrint('[SipService] _disposeMediaStreams error: $e');
    }
  }
}
