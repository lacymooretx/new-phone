import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:just_audio/just_audio.dart';

// ---------------------------------------------------------------------------
// Audio route types
// ---------------------------------------------------------------------------

/// Available audio output routes.
enum AudioRoute {
  /// Device earpiece (default for voice calls).
  earpiece,

  /// Built-in speaker.
  speaker,

  /// Bluetooth headset / car kit.
  bluetooth,

  /// Wired headset (3.5 mm or USB-C).
  wiredHeadset,
}

/// Describes a single audio output device.
class AudioDevice {
  final String id;
  final String name;
  final AudioRoute route;

  /// Whether this device is currently selected.
  final bool isActive;

  const AudioDevice({
    required this.id,
    required this.name,
    required this.route,
    this.isActive = false,
  });

  AudioDevice copyWith({
    String? id,
    String? name,
    AudioRoute? route,
    bool? isActive,
  }) =>
      AudioDevice(
        id: id ?? this.id,
        name: name ?? this.name,
        route: route ?? this.route,
        isActive: isActive ?? this.isActive,
      );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AudioDevice &&
          runtimeType == other.runtimeType &&
          id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() => 'AudioDevice(id: $id, name: $name, route: $route)';
}

// ---------------------------------------------------------------------------
// Abstract audio service
// ---------------------------------------------------------------------------

/// Manages audio routing for voice calls.
///
/// Handles switching between earpiece, speaker, Bluetooth, and wired headset
/// outputs. Monitors hardware changes (Bluetooth connect/disconnect, headset
/// plug/unplug) and updates the available device list.
abstract class AudioService {
  /// Get the list of currently available audio output devices.
  Future<List<AudioDevice>> getAudioDevices();

  /// Set the active audio output route.
  Future<void> setAudioRoute(AudioRoute route);

  /// Get the currently active audio route.
  AudioRoute get currentRoute;

  /// Stream of audio route changes (triggered by user action or hardware
  /// events like Bluetooth disconnect).
  Stream<AudioRoute> get audioRouteStream;

  /// Stream of available audio device list changes.
  Stream<List<AudioDevice>> get audioDevicesStream;

  /// Play the ringtone for an incoming call.
  Future<void> playRingtone();

  /// Stop the ringtone.
  Future<void> stopRingtone();

  /// Play a short DTMF feedback tone for the given digit.
  Future<void> playDtmfTone(String digit);

  /// Dispose of platform resources and listeners.
  void dispose();
}

// ---------------------------------------------------------------------------
// Default implementation
// ---------------------------------------------------------------------------

/// DTMF tone frequencies (row freq, col freq) for standard telephone keypad.
const Map<String, List<int>> _dtmfFrequencies = {
  '1': [697, 1209],
  '2': [697, 1336],
  '3': [697, 1477],
  '4': [770, 1209],
  '5': [770, 1336],
  '6': [770, 1477],
  '7': [852, 1209],
  '8': [852, 1336],
  '9': [852, 1477],
  '*': [941, 1209],
  '0': [941, 1336],
  '#': [941, 1477],
};

/// Default [AudioService] implementation.
///
/// Uses platform channels to interact with iOS AVAudioSession / Android
/// AudioManager for audio routing. Uses just_audio for ringtone and DTMF
/// tone playback.
class DefaultAudioService implements AudioService {
  AudioRoute _currentRoute = AudioRoute.earpiece;

  final _routeController = StreamController<AudioRoute>.broadcast();
  final _devicesController = StreamController<List<AudioDevice>>.broadcast();

  /// Internal device list, updated by the platform listener.
  List<AudioDevice> _devices = [
    const AudioDevice(
      id: 'earpiece',
      name: 'Earpiece',
      route: AudioRoute.earpiece,
      isActive: true,
    ),
    const AudioDevice(
      id: 'speaker',
      name: 'Speaker',
      route: AudioRoute.speaker,
    ),
  ];

  /// Player for ringtone audio.
  AudioPlayer? _ringtonePlayer;

  /// Player for DTMF feedback tones.
  AudioPlayer? _dtmfPlayer;

  /// Platform channel for native audio routing control.
  static const MethodChannel _audioChannel =
      MethodChannel('com.newphone/audio');

  /// Whether audio focus is currently held.
  bool _hasAudioFocus = false;

  DefaultAudioService() {
    _startDeviceMonitoring();
  }

  @override
  AudioRoute get currentRoute => _currentRoute;

  @override
  Stream<AudioRoute> get audioRouteStream => _routeController.stream;

  @override
  Stream<List<AudioDevice>> get audioDevicesStream =>
      _devicesController.stream;

  @override
  Future<List<AudioDevice>> getAudioDevices() async {
    try {
      final result = await _audioChannel.invokeMethod<List<dynamic>>(
        'getAudioDevices',
      );

      if (result != null) {
        _devices = result.map((d) {
          final map = Map<String, dynamic>.from(d as Map);
          return AudioDevice(
            id: map['id'] as String,
            name: map['name'] as String,
            route: _routeFromString(map['type'] as String),
            isActive: map['isActive'] as bool? ?? false,
          );
        }).toList();

        // Update current route from the active device.
        final activeDevice = _devices.where((d) => d.isActive).firstOrNull;
        if (activeDevice != null && activeDevice.route != _currentRoute) {
          _currentRoute = activeDevice.route;
          _routeController.add(_currentRoute);
        }

        _devicesController.add(List.unmodifiable(_devices));
      }
    } on MissingPluginException {
      // Platform channel not available (e.g., running in test/simulator).
      // Return the default device list.
      debugPrint(
        '[AudioService] Platform channel not available, using defaults',
      );
    } catch (e) {
      debugPrint('[AudioService] getAudioDevices failed: $e');
    }

    return List.unmodifiable(_devices);
  }

  @override
  Future<void> setAudioRoute(AudioRoute route) async {
    if (route == _currentRoute) return;

    final previousRoute = _currentRoute;

    try {
      await _audioChannel.invokeMethod('setAudioRoute', {
        'route': route.name,
      });
    } on MissingPluginException {
      // Platform channel not available — update state locally.
      debugPrint(
        '[AudioService] Platform channel not available, setting route locally',
      );
    } catch (e) {
      debugPrint('[AudioService] setAudioRoute platform call failed: $e');
    }

    _currentRoute = route;

    // Update device active flags.
    _devices = _devices.map((d) {
      return d.copyWith(isActive: d.route == route);
    }).toList();

    _routeController.add(route);
    _devicesController.add(List.unmodifiable(_devices));

    debugPrint(
      '[AudioService] Route changed: $previousRoute -> $route',
    );
  }

  @override
  Future<void> playRingtone() async {
    try {
      await stopRingtone();

      _ringtonePlayer = AudioPlayer();

      // Request audio focus for the ringtone.
      await _requestAudioFocus();

      // Load the ringtone asset. Falls back to a default system sound
      // if the custom asset is not available.
      try {
        await _ringtonePlayer!.setAsset('assets/audio/ringtone.mp3');
      } catch (_) {
        // If custom ringtone is not bundled, use a short looping tone.
        debugPrint(
          '[AudioService] Custom ringtone not found, using default',
        );
        await _ringtonePlayer!.setAsset('assets/audio/default_ring.mp3');
      }

      // Loop the ringtone until stopped.
      await _ringtonePlayer!.setLoopMode(LoopMode.one);

      // Play at full volume through the speaker/ringer.
      await _ringtonePlayer!.setVolume(1.0);
      await _ringtonePlayer!.play();

      debugPrint('[AudioService] Ringtone playing');
    } catch (e) {
      debugPrint('[AudioService] playRingtone failed: $e');
    }
  }

  @override
  Future<void> stopRingtone() async {
    try {
      if (_ringtonePlayer != null) {
        await _ringtonePlayer!.stop();
        await _ringtonePlayer!.dispose();
        _ringtonePlayer = null;

        debugPrint('[AudioService] Ringtone stopped');
      }
    } catch (e) {
      debugPrint('[AudioService] stopRingtone failed: $e');
    }
  }

  @override
  Future<void> playDtmfTone(String digit) async {
    if (!_dtmfFrequencies.containsKey(digit)) {
      debugPrint('[AudioService] Invalid DTMF digit: $digit');
      return;
    }

    try {
      // Dispose any previous DTMF player to avoid overlapping tones.
      await _dtmfPlayer?.dispose();
      _dtmfPlayer = AudioPlayer();

      // Load the DTMF tone asset for the specific digit.
      try {
        await _dtmfPlayer!.setAsset('assets/audio/dtmf_$digit.mp3');
      } catch (_) {
        // If per-digit assets are not available, use a generic tone.
        try {
          await _dtmfPlayer!.setAsset('assets/audio/dtmf_tone.mp3');
        } catch (_) {
          debugPrint('[AudioService] No DTMF tone assets available');
          await _dtmfPlayer!.dispose();
          _dtmfPlayer = null;
          return;
        }
      }

      // Play the DTMF tone once, at moderate volume, short duration.
      await _dtmfPlayer!.setVolume(0.5);
      await _dtmfPlayer!.play();

      // Dispose after playback completes.
      _dtmfPlayer!.playerStateStream.listen((playerState) {
        if (playerState.processingState == ProcessingState.completed) {
          _dtmfPlayer?.dispose();
          _dtmfPlayer = null;
        }
      });

      debugPrint('[AudioService] DTMF tone played: $digit');
    } catch (e) {
      debugPrint('[AudioService] playDtmfTone failed: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Audio focus management
  // ---------------------------------------------------------------------------

  /// Request audio focus from the OS for voice call audio.
  Future<void> _requestAudioFocus() async {
    if (_hasAudioFocus) return;

    try {
      await _audioChannel.invokeMethod('requestAudioFocus', {
        'usage': 'voiceCommunication',
        'contentType': 'speech',
      });
      _hasAudioFocus = true;
      debugPrint('[AudioService] Audio focus acquired');
    } on MissingPluginException {
      _hasAudioFocus = true;
      debugPrint(
        '[AudioService] Platform channel not available, '
        'assuming audio focus',
      );
    } catch (e) {
      debugPrint('[AudioService] requestAudioFocus failed: $e');
    }
  }

  /// Release audio focus back to the OS.
  Future<void> releaseAudioFocus() async {
    if (!_hasAudioFocus) return;

    try {
      await _audioChannel.invokeMethod('releaseAudioFocus');
      _hasAudioFocus = false;
      debugPrint('[AudioService] Audio focus released');
    } on MissingPluginException {
      _hasAudioFocus = false;
    } catch (e) {
      debugPrint('[AudioService] releaseAudioFocus failed: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Device simulation (for testing / development)
  // ---------------------------------------------------------------------------

  /// Simulate a Bluetooth device connecting (for development / testing).
  @visibleForTesting
  void simulateBluetoothConnected(String deviceName) {
    final btDevice = AudioDevice(
      id: 'bt_${deviceName.toLowerCase().replaceAll(' ', '_')}',
      name: deviceName,
      route: AudioRoute.bluetooth,
    );

    if (!_devices.contains(btDevice)) {
      _devices = [..._devices, btDevice];
      _devicesController.add(List.unmodifiable(_devices));
      debugPrint(
        '[AudioService] Bluetooth connected: $deviceName',
      );
    }
  }

  /// Simulate a Bluetooth device disconnecting.
  @visibleForTesting
  void simulateBluetoothDisconnected(String deviceId) {
    final removed = _devices.where((d) => d.id != deviceId).toList();
    if (removed.length != _devices.length) {
      _devices = removed;

      // If the disconnected device was active, fall back to earpiece.
      if (_currentRoute == AudioRoute.bluetooth) {
        _currentRoute = AudioRoute.earpiece;
        _devices = _devices.map((d) {
          return d.copyWith(isActive: d.route == AudioRoute.earpiece);
        }).toList();
        _routeController.add(_currentRoute);
      }

      _devicesController.add(List.unmodifiable(_devices));
      debugPrint(
        '[AudioService] Bluetooth disconnected: $deviceId',
      );
    }
  }

  /// Simulate a wired headset plug event.
  @visibleForTesting
  void simulateWiredHeadsetPlugged(bool plugged) {
    if (plugged) {
      final device = const AudioDevice(
        id: 'wired_headset',
        name: 'Wired Headset',
        route: AudioRoute.wiredHeadset,
      );
      if (!_devices.contains(device)) {
        _devices = [..._devices, device];

        // Auto-switch to wired headset when plugged in.
        _currentRoute = AudioRoute.wiredHeadset;
        _devices = _devices.map((d) {
          return d.copyWith(isActive: d.route == AudioRoute.wiredHeadset);
        }).toList();

        _routeController.add(_currentRoute);
        _devicesController.add(List.unmodifiable(_devices));
      }
    } else {
      _devices =
          _devices.where((d) => d.route != AudioRoute.wiredHeadset).toList();

      if (_currentRoute == AudioRoute.wiredHeadset) {
        _currentRoute = AudioRoute.earpiece;
        _devices = _devices.map((d) {
          return d.copyWith(isActive: d.route == AudioRoute.earpiece);
        }).toList();
        _routeController.add(_currentRoute);
      }

      _devicesController.add(List.unmodifiable(_devices));
    }
  }

  // ---------------------------------------------------------------------------
  // Private
  // ---------------------------------------------------------------------------

  void _startDeviceMonitoring() {
    // Set up platform channel listener for audio route changes.
    // On iOS: AVAudioSession.routeChangeNotification
    // On Android: AudioManager.registerAudioDeviceCallback
    _audioChannel.setMethodCallHandler((call) async {
      switch (call.method) {
        case 'onAudioRouteChanged':
          final routeStr = call.arguments['route'] as String?;
          if (routeStr != null) {
            final route = _routeFromString(routeStr);
            if (route != _currentRoute) {
              _currentRoute = route;
              _devices = _devices.map((d) {
                return d.copyWith(isActive: d.route == route);
              }).toList();

              _routeController.add(_currentRoute);
              _devicesController.add(List.unmodifiable(_devices));

              debugPrint(
                '[AudioService] Route changed via platform: $route',
              );
            }
          }

        case 'onAudioDevicesChanged':
          // Re-query devices when the platform reports a change.
          await getAudioDevices();

        default:
          debugPrint(
            '[AudioService] Unknown platform callback: ${call.method}',
          );
      }
    });
  }

  /// Convert a string route name to an [AudioRoute] enum value.
  AudioRoute _routeFromString(String routeStr) {
    switch (routeStr.toLowerCase()) {
      case 'earpiece':
      case 'receiver':
      case 'builtinreceiver':
        return AudioRoute.earpiece;
      case 'speaker':
      case 'builtinspeaker':
        return AudioRoute.speaker;
      case 'bluetooth':
      case 'bluetootha2dp':
      case 'bluetoothsco':
      case 'bluetoothe':
        return AudioRoute.bluetooth;
      case 'wiredheadset':
      case 'headset':
      case 'headphone':
      case 'headphones':
        return AudioRoute.wiredHeadset;
      default:
        return AudioRoute.earpiece;
    }
  }

  @override
  void dispose() {
    _ringtonePlayer?.dispose();
    _dtmfPlayer?.dispose();
    releaseAudioFocus();
    _routeController.close();
    _devicesController.close();
  }
}
