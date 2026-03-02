import 'dart:async';

import 'package:flutter/foundation.dart';

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

  /// Dispose of platform resources and listeners.
  void dispose();
}

// ---------------------------------------------------------------------------
// Default implementation
// ---------------------------------------------------------------------------

/// Default [AudioService] implementation.
///
/// Uses platform channels to interact with iOS AVAudioSession / Android
/// AudioManager. Until the native bridge is wired, the core logic is stubbed
/// with sensible defaults so the UI can be built against it.
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

  DefaultAudioService() {
    _startDeviceMonitoring();
  }

  @override
  AudioRoute get currentRoute => _currentRoute;

  @override
  Stream<AudioRoute> get audioRouteStream => _routeController.stream;

  @override
  Stream<List<AudioDevice>> get audioDevicesStream => _devicesController.stream;

  @override
  Future<List<AudioDevice>> getAudioDevices() async {
    // TODO: Query platform for real device list:
    //   iOS  — AVAudioSession.sharedInstance().availableInputs
    //   Android — AudioManager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)

    return List.unmodifiable(_devices);
  }

  @override
  Future<void> setAudioRoute(AudioRoute route) async {
    if (route == _currentRoute) return;

    // TODO: Apply route via platform channel:
    //   iOS  — AVAudioSession.sharedInstance().overrideOutputAudioPort(...)
    //          or setPreferredInput(...) for Bluetooth
    //   Android — AudioManager.setSpeakerphoneOn(...)
    //             or AudioManager.setBluetoothScoOn(...)

    final previousRoute = _currentRoute;
    _currentRoute = route;

    // Update device active flags
    _devices = _devices.map((d) {
      return d.copyWith(isActive: d.route == route);
    }).toList();

    _routeController.add(route);
    _devicesController.add(List.unmodifiable(_devices));

    debugPrint(
      '[AudioService] Route changed: $previousRoute -> $route',
    );
  }

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

      // If the disconnected device was active, fall back to earpiece
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

        // Auto-switch to wired headset when plugged in
        _currentRoute = AudioRoute.wiredHeadset;
        _devices = _devices.map((d) {
          return d.copyWith(isActive: d.route == AudioRoute.wiredHeadset);
        }).toList();

        _routeController.add(_currentRoute);
        _devicesController.add(List.unmodifiable(_devices));
      }
    } else {
      _devices = _devices.where((d) => d.route != AudioRoute.wiredHeadset).toList();

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

  void _startDeviceMonitoring() {
    // TODO: Set up platform channel listener for audio route changes:
    //   iOS  — AVAudioSession.routeChangeNotification
    //   Android — AudioManager.registerAudioDeviceCallback
    //
    // On change, re-query devices and update _devices, _currentRoute,
    // emit to streams.
  }

  @override
  void dispose() {
    _routeController.close();
    _devicesController.close();
  }
}
