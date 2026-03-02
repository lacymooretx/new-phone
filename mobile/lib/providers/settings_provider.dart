import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

// ---------------------------------------------------------------------------
// Settings state
// ---------------------------------------------------------------------------

/// Persisted app settings state.
class SettingsState {
  final ThemeMode themeMode;
  final bool biometricEnabled;
  final bool pushEnabled;
  final bool voicemailNotifications;
  final bool smsNotifications;
  final String defaultAudioOutput; // 'earpiece' | 'speaker'
  final String ringtone; // 'default' | 'classic' | 'digital' | 'gentle' | 'urgent'

  const SettingsState({
    this.themeMode = ThemeMode.system,
    this.biometricEnabled = false,
    this.pushEnabled = true,
    this.voicemailNotifications = true,
    this.smsNotifications = true,
    this.defaultAudioOutput = 'earpiece',
    this.ringtone = 'default',
  });

  SettingsState copyWith({
    ThemeMode? themeMode,
    bool? biometricEnabled,
    bool? pushEnabled,
    bool? voicemailNotifications,
    bool? smsNotifications,
    String? defaultAudioOutput,
    String? ringtone,
  }) =>
      SettingsState(
        themeMode: themeMode ?? this.themeMode,
        biometricEnabled: biometricEnabled ?? this.biometricEnabled,
        pushEnabled: pushEnabled ?? this.pushEnabled,
        voicemailNotifications:
            voicemailNotifications ?? this.voicemailNotifications,
        smsNotifications: smsNotifications ?? this.smsNotifications,
        defaultAudioOutput: defaultAudioOutput ?? this.defaultAudioOutput,
        ringtone: ringtone ?? this.ringtone,
      );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SettingsState &&
          runtimeType == other.runtimeType &&
          themeMode == other.themeMode &&
          biometricEnabled == other.biometricEnabled &&
          pushEnabled == other.pushEnabled &&
          voicemailNotifications == other.voicemailNotifications &&
          smsNotifications == other.smsNotifications &&
          defaultAudioOutput == other.defaultAudioOutput &&
          ringtone == other.ringtone;

  @override
  int get hashCode => Object.hash(
        themeMode,
        biometricEnabled,
        pushEnabled,
        voicemailNotifications,
        smsNotifications,
        defaultAudioOutput,
        ringtone,
      );
}

// ---------------------------------------------------------------------------
// Storage keys
// ---------------------------------------------------------------------------

const _keyThemeMode = 'np_settings_theme_mode';
const _keyBiometric = 'np_settings_biometric';
const _keyPush = 'np_settings_push';
const _keyVoicemailNotif = 'np_settings_voicemail_notif';
const _keySmsNotif = 'np_settings_sms_notif';
const _keyAudioOutput = 'np_settings_audio_output';
const _keyRingtone = 'np_settings_ringtone';

// ---------------------------------------------------------------------------
// Settings provider
// ---------------------------------------------------------------------------

/// Settings state notifier — persists to FlutterSecureStorage.
///
/// Uses secure storage to keep settings encrypted alongside auth tokens.
/// Provides typed getters/setters for each setting.
final settingsProvider =
    StateNotifierProvider<SettingsNotifier, SettingsState>((ref) {
  return SettingsNotifier();
});

class SettingsNotifier extends StateNotifier<SettingsState> {
  final FlutterSecureStorage _storage;
  bool _loaded = false;

  SettingsNotifier({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage(),
        super(const SettingsState());

  /// Whether settings have been loaded from storage.
  bool get isLoaded => _loaded;

  /// Load settings from persistent storage.
  ///
  /// Call once during app startup (after WidgetsFlutterBinding.ensureInitialized).
  Future<void> load() async {
    if (_loaded) return;

    try {
      final themeModeStr = await _storage.read(key: _keyThemeMode);
      final biometricStr = await _storage.read(key: _keyBiometric);
      final pushStr = await _storage.read(key: _keyPush);
      final vmNotifStr = await _storage.read(key: _keyVoicemailNotif);
      final smsNotifStr = await _storage.read(key: _keySmsNotif);
      final audioOutput = await _storage.read(key: _keyAudioOutput);
      final ringtone = await _storage.read(key: _keyRingtone);

      state = SettingsState(
        themeMode: _parseThemeMode(themeModeStr),
        biometricEnabled: biometricStr == 'true',
        pushEnabled: pushStr != 'false', // default true
        voicemailNotifications: vmNotifStr != 'false', // default true
        smsNotifications: smsNotifStr != 'false', // default true
        defaultAudioOutput: audioOutput ?? 'earpiece',
        ringtone: ringtone ?? 'default',
      );

      _loaded = true;
    } catch (e) {
      // If storage fails, keep defaults
      _loaded = true;
    }
  }

  // ---------------------------------------------------------------------------
  // Individual setters
  // ---------------------------------------------------------------------------

  Future<void> setThemeMode(ThemeMode mode) async {
    state = state.copyWith(themeMode: mode);
    await _storage.write(key: _keyThemeMode, value: mode.name);
  }

  Future<void> setBiometricEnabled(bool enabled) async {
    state = state.copyWith(biometricEnabled: enabled);
    await _storage.write(key: _keyBiometric, value: enabled.toString());
  }

  Future<void> setPushEnabled(bool enabled) async {
    state = state.copyWith(pushEnabled: enabled);
    await _storage.write(key: _keyPush, value: enabled.toString());
  }

  Future<void> setVoicemailNotifications(bool enabled) async {
    state = state.copyWith(voicemailNotifications: enabled);
    await _storage.write(key: _keyVoicemailNotif, value: enabled.toString());
  }

  Future<void> setSmsNotifications(bool enabled) async {
    state = state.copyWith(smsNotifications: enabled);
    await _storage.write(key: _keySmsNotif, value: enabled.toString());
  }

  Future<void> setDefaultAudioOutput(String output) async {
    state = state.copyWith(defaultAudioOutput: output);
    await _storage.write(key: _keyAudioOutput, value: output);
  }

  Future<void> setRingtone(String ringtone) async {
    state = state.copyWith(ringtone: ringtone);
    await _storage.write(key: _keyRingtone, value: ringtone);
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  static ThemeMode _parseThemeMode(String? value) => switch (value) {
        'light' => ThemeMode.light,
        'dark' => ThemeMode.dark,
        _ => ThemeMode.system,
      };
}
