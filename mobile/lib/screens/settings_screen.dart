import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:just_audio/just_audio.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config/app_config.dart';
import '../models/user.dart';
import '../providers/auth_provider.dart';
import '../providers/settings_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/avatar_widget.dart';
import '../widgets/section_header.dart';

/// Full settings screen replacing the placeholder SettingsTab.
///
/// Sections: Account, Server, Audio, Notifications, Appearance, Security,
/// About, Sign Out.
class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  @override
  void initState() {
    super.initState();
    // Ensure settings are loaded
    final notifier = ref.read(settingsProvider.notifier);
    if (!notifier.isLoaded) {
      notifier.load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final authState = ref.watch(authProvider);
    final settings = ref.watch(settingsProvider);

    User? user;
    if (authState is AuthAuthenticated) {
      user = authState.user;
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        children: [
          // ---------------------------------------------------------------
          // Account section
          // ---------------------------------------------------------------
          if (user != null) _buildAccountCard(user, theme, colorScheme),

          // ---------------------------------------------------------------
          // Server section
          // ---------------------------------------------------------------
          const SectionHeader(title: 'Server'),
          _buildServerTile(theme, colorScheme),

          // ---------------------------------------------------------------
          // Audio section
          // ---------------------------------------------------------------
          const SectionHeader(title: 'Audio'),
          _buildAudioOutputTile(settings, theme),
          ListTile(
            leading: const Icon(Icons.music_note_outlined),
            title: const Text('Ringtone'),
            subtitle: Text(_ringtoneDisplayName(settings.ringtone)),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _showRingtoneSelector(settings.ringtone),
          ),

          // ---------------------------------------------------------------
          // Notifications section
          // ---------------------------------------------------------------
          const SectionHeader(title: 'Notifications'),
          SwitchListTile(
            secondary: const Icon(Icons.notifications_outlined),
            title: const Text('Push Notifications'),
            subtitle: const Text('Receive push notifications'),
            value: settings.pushEnabled,
            onChanged: (value) {
              ref.read(settingsProvider.notifier).setPushEnabled(value);
            },
          ),
          SwitchListTile(
            secondary: const Icon(Icons.voicemail_outlined),
            title: const Text('Voicemail Notifications'),
            subtitle: const Text('Notify on new voicemail'),
            value: settings.voicemailNotifications,
            onChanged: settings.pushEnabled
                ? (value) {
                    ref
                        .read(settingsProvider.notifier)
                        .setVoicemailNotifications(value);
                  }
                : null,
          ),
          SwitchListTile(
            secondary: const Icon(Icons.sms_outlined),
            title: const Text('SMS Notifications'),
            subtitle: const Text('Notify on new messages'),
            value: settings.smsNotifications,
            onChanged: settings.pushEnabled
                ? (value) {
                    ref
                        .read(settingsProvider.notifier)
                        .setSmsNotifications(value);
                  }
                : null,
          ),

          // ---------------------------------------------------------------
          // Appearance section
          // ---------------------------------------------------------------
          const SectionHeader(title: 'Appearance'),
          _buildThemeTile(settings, theme),

          // ---------------------------------------------------------------
          // Security section
          // ---------------------------------------------------------------
          const SectionHeader(title: 'Security'),
          SwitchListTile(
            secondary: const Icon(Icons.fingerprint),
            title: const Text('Biometric Login'),
            subtitle: Text(
              _biometricLabel,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            value: settings.biometricEnabled,
            onChanged: (value) {
              ref.read(settingsProvider.notifier).setBiometricEnabled(value);
            },
          ),
          ListTile(
            leading: const Icon(Icons.lock_outline),
            title: const Text('Change Password'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push('/settings/change-password'),
          ),

          // ---------------------------------------------------------------
          // About section
          // ---------------------------------------------------------------
          const SectionHeader(title: 'About'),
          ListTile(
            leading: const Icon(Icons.info_outline),
            title: const Text('App Version'),
            subtitle: Text(
              '${AppConfig.appVersion} (${AppConfig.environment.name})',
            ),
          ),
          ListTile(
            leading: const Icon(Icons.description_outlined),
            title: const Text('Licenses'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              showLicensePage(
                context: context,
                applicationName: AppConfig.appName,
                applicationVersion: AppConfig.appVersion,
              );
            },
          ),
          ListTile(
            leading: const Icon(Icons.support_agent_outlined),
            title: const Text('Support'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _launchSupport(),
          ),

          // ---------------------------------------------------------------
          // Sign Out
          // ---------------------------------------------------------------
          const SizedBox(height: 16),
          const Divider(),
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppThemeExtras.spaceMd,
              vertical: AppThemeExtras.spaceSm,
            ),
            child: FilledButton.tonal(
              onPressed: () => _confirmSignOut(context, colorScheme),
              style: FilledButton.styleFrom(
                foregroundColor: colorScheme.error,
                backgroundColor: colorScheme.errorContainer.withOpacity(0.3),
                minimumSize: const Size(double.infinity, 52),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.logout),
                  SizedBox(width: 8),
                  Text(
                    'Sign Out',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 32),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Account card
  // ---------------------------------------------------------------------------

  Widget _buildAccountCard(
    User user,
    ThemeData theme,
    ColorScheme colorScheme,
  ) {
    final displayName = user.displayName ?? user.email ?? 'User';

    return Padding(
      padding: const EdgeInsets.all(AppThemeExtras.spaceMd),
      child: Card(
        elevation: 0,
        color: colorScheme.surfaceContainerHighest.withOpacity(0.3),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppThemeExtras.radiusMd),
        ),
        child: Padding(
          padding: const EdgeInsets.all(AppThemeExtras.spaceMd),
          child: Row(
            children: [
              AvatarWidget(
                name: displayName,
                size: AvatarSize.large,
              ),
              const SizedBox(width: AppThemeExtras.spaceMd),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      displayName,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    if (user.email != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        user.email!,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                    const SizedBox(height: AppThemeExtras.spaceXs),
                    _RoleBadge(role: user.role),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.edit_outlined),
                tooltip: 'Edit Profile',
                onPressed: () => _showEditProfileDialog(user),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Server tile
  // ---------------------------------------------------------------------------

  Widget _buildServerTile(ThemeData theme, ColorScheme colorScheme) {
    return FutureBuilder<String>(
      future: ref.read(authServiceProvider).loadServerUrl(),
      builder: (context, snapshot) {
        final serverUrl = snapshot.data ?? AppConfig.defaultApiBaseUrl;

        return ListTile(
          leading: const Icon(Icons.dns_outlined),
          title: const Text('Connected Server'),
          subtitle: Text(serverUrl),
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: AppThemeExtras.statusAvailable,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 4),
              Text(
                'Connected',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: AppThemeExtras.statusAvailable,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  // ---------------------------------------------------------------------------
  // Audio output tile
  // ---------------------------------------------------------------------------

  Widget _buildAudioOutputTile(SettingsState settings, ThemeData theme) {
    return ListTile(
      leading: Icon(
        settings.defaultAudioOutput == 'speaker'
            ? Icons.volume_up
            : Icons.hearing,
      ),
      title: const Text('Default Audio Output'),
      subtitle: Text(
        settings.defaultAudioOutput == 'speaker' ? 'Speaker' : 'Earpiece',
      ),
      trailing: SegmentedButton<String>(
        segments: const [
          ButtonSegment(
            value: 'earpiece',
            icon: Icon(Icons.hearing, size: 16),
          ),
          ButtonSegment(
            value: 'speaker',
            icon: Icon(Icons.volume_up, size: 16),
          ),
        ],
        selected: {settings.defaultAudioOutput},
        onSelectionChanged: (selected) {
          ref
              .read(settingsProvider.notifier)
              .setDefaultAudioOutput(selected.first);
        },
        showSelectedIcon: false,
        style: ButtonStyle(
          visualDensity: VisualDensity.compact,
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Theme selector tile
  // ---------------------------------------------------------------------------

  Widget _buildThemeTile(SettingsState settings, ThemeData theme) {
    return ListTile(
      leading: Icon(
        settings.themeMode == ThemeMode.dark
            ? Icons.dark_mode
            : settings.themeMode == ThemeMode.light
                ? Icons.light_mode
                : Icons.brightness_auto,
      ),
      title: const Text('Theme'),
      subtitle: Text(_themeModeLabel(settings.themeMode)),
      trailing: SegmentedButton<ThemeMode>(
        segments: const [
          ButtonSegment(
            value: ThemeMode.system,
            icon: Icon(Icons.brightness_auto, size: 16),
          ),
          ButtonSegment(
            value: ThemeMode.light,
            icon: Icon(Icons.light_mode, size: 16),
          ),
          ButtonSegment(
            value: ThemeMode.dark,
            icon: Icon(Icons.dark_mode, size: 16),
          ),
        ],
        selected: {settings.themeMode},
        onSelectionChanged: (selected) {
          ref.read(settingsProvider.notifier).setThemeMode(selected.first);
        },
        showSelectedIcon: false,
        style: ButtonStyle(
          visualDensity: VisualDensity.compact,
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Sign out
  // ---------------------------------------------------------------------------

  Future<void> _confirmSignOut(
    BuildContext context,
    ColorScheme colorScheme,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Sign Out'),
        content: const Text(
          'Are you sure you want to sign out? You will need to sign in again to use the app.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: colorScheme.error,
              foregroundColor: colorScheme.onError,
            ),
            child: const Text('Sign Out'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      await ref.read(authProvider.notifier).logout();
      if (context.mounted) {
        context.go('/login');
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  String get _biometricLabel {
    // In a real app, check TargetPlatform for the right label
    return 'Use Face ID or Fingerprint to unlock';
  }

  String _themeModeLabel(ThemeMode mode) => switch (mode) {
        ThemeMode.system => 'System default',
        ThemeMode.light => 'Light',
        ThemeMode.dark => 'Dark',
      };

  // ---------------------------------------------------------------------------
  // Ringtone selector (4B)
  // ---------------------------------------------------------------------------

  /// Map of ringtone IDs to display names.
  static const _ringtones = {
    'default': 'Default',
    'classic': 'Classic',
    'digital': 'Digital',
    'gentle': 'Gentle',
    'urgent': 'Urgent',
  };

  String _ringtoneDisplayName(String id) => _ringtones[id] ?? 'Default';

  void _showRingtoneSelector(String currentRingtone) {
    String selectedRingtone = currentRingtone;
    AudioPlayer? previewPlayer;

    showModalBottomSheet<void>(
      context: context,
      builder: (bottomSheetContext) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return SafeArea(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                    child: Text(
                      'Select Ringtone',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                  ),
                  ..._ringtones.entries.map((entry) {
                    final isSelected = entry.key == selectedRingtone;
                    return ListTile(
                      leading: Icon(
                        isSelected
                            ? Icons.radio_button_checked
                            : Icons.radio_button_unchecked,
                        color: isSelected
                            ? Theme.of(context).colorScheme.primary
                            : null,
                      ),
                      title: Text(entry.value),
                      trailing: IconButton(
                        icon: const Icon(Icons.play_circle_outline),
                        tooltip: 'Preview',
                        onPressed: () async {
                          // Stop any ongoing preview
                          await previewPlayer?.stop();
                          await previewPlayer?.dispose();
                          previewPlayer = AudioPlayer();
                          try {
                            await previewPlayer!.setAsset(
                              'assets/audio/ringtone_${entry.key}.mp3',
                            );
                            await previewPlayer!.play();
                          } catch (_) {
                            // Asset may not exist in dev; ignore
                          }
                        },
                      ),
                      onTap: () {
                        setModalState(() {
                          selectedRingtone = entry.key;
                        });
                      },
                    );
                  }),
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 8,
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        TextButton(
                          onPressed: () {
                            previewPlayer?.stop();
                            previewPlayer?.dispose();
                            Navigator.of(context).pop();
                          },
                          child: const Text('Cancel'),
                        ),
                        const SizedBox(width: 8),
                        FilledButton(
                          onPressed: () {
                            previewPlayer?.stop();
                            previewPlayer?.dispose();
                            ref
                                .read(settingsProvider.notifier)
                                .setRingtone(selectedRingtone);
                            Navigator.of(context).pop();
                          },
                          child: const Text('Save'),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    ).whenComplete(() {
      // Ensure preview is cleaned up if sheet is dismissed
      previewPlayer?.stop();
      previewPlayer?.dispose();
    });
  }

  // ---------------------------------------------------------------------------
  // Profile editing dialog (4C)
  // ---------------------------------------------------------------------------

  void _showEditProfileDialog(User user) {
    // Split displayName into first/last name for the form
    final parts = (user.displayName ?? '').split(' ');
    final firstNameController = TextEditingController(
      text: parts.isNotEmpty ? parts.first : '',
    );
    final lastNameController = TextEditingController(
      text: parts.length > 1 ? parts.sublist(1).join(' ') : '',
    );

    showDialog(
      context: context,
      builder: (dialogContext) {
        bool isSaving = false;
        String? errorMessage;

        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('Edit Profile'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (errorMessage != null) ...[
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.errorContainer,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        errorMessage!,
                        style: TextStyle(
                          color:
                              Theme.of(context).colorScheme.onErrorContainer,
                          fontSize: 13,
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                  ],
                  TextField(
                    controller: firstNameController,
                    decoration: const InputDecoration(
                      labelText: 'First Name',
                      prefixIcon: Icon(Icons.person_outline),
                    ),
                    textInputAction: TextInputAction.next,
                    textCapitalization: TextCapitalization.words,
                    enabled: !isSaving,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: lastNameController,
                    decoration: const InputDecoration(
                      labelText: 'Last Name',
                      prefixIcon: Icon(Icons.person_outline),
                    ),
                    textInputAction: TextInputAction.done,
                    textCapitalization: TextCapitalization.words,
                    enabled: !isSaving,
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: isSaving
                      ? null
                      : () => Navigator.of(context).pop(),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: isSaving
                      ? null
                      : () async {
                          setDialogState(() {
                            isSaving = true;
                            errorMessage = null;
                          });

                          try {
                            final api = ref.read(apiServiceProvider);
                            final firstName =
                                firstNameController.text.trim();
                            final lastName =
                                lastNameController.text.trim();
                            final displayName = lastName.isNotEmpty
                                ? '$firstName $lastName'
                                : firstName;

                            await api.patch(
                              '/tenants/${user.tenantId}/users/${user.id}',
                              data: {
                                'first_name': firstName,
                                'last_name': lastName,
                                'display_name': displayName,
                              },
                            );

                            // The display name in the JWT will update on
                            // next token refresh. Show success feedback now.
                            if (context.mounted) {
                              Navigator.of(context).pop();
                              ScaffoldMessenger.of(this.context).showSnackBar(
                                const SnackBar(
                                  content: Text('Profile updated'),
                                ),
                              );
                            }
                          } on DioException catch (e) {
                            final msg = _extractProfileErrorMessage(e);
                            setDialogState(() {
                              isSaving = false;
                              errorMessage = msg;
                            });
                          } catch (e) {
                            setDialogState(() {
                              isSaving = false;
                              errorMessage =
                                  'An unexpected error occurred.';
                            });
                          }
                        },
                  child: isSaving
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                          ),
                        )
                      : const Text('Save'),
                ),
              ],
            );
          },
        );
      },
    ).whenComplete(() {
      firstNameController.dispose();
      lastNameController.dispose();
    });
  }

  String _extractProfileErrorMessage(DioException e) {
    if (e.response?.data is Map<String, dynamic>) {
      final data = e.response!.data as Map<String, dynamic>;
      if (data.containsKey('detail')) {
        final detail = data['detail'];
        if (detail is String) return detail;
      }
    }
    final code = e.response?.statusCode;
    if (code == 403) return 'You do not have permission to edit this profile.';
    if (code == 404) return 'User not found.';
    if (code != null && code >= 500) return 'Server error. Try again later.';
    return 'Could not update profile.';
  }

  // ---------------------------------------------------------------------------
  // Support action (4D)
  // ---------------------------------------------------------------------------

  Future<void> _launchSupport() async {
    final uri = Uri.parse('mailto:support@aspendora.com');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Could not open email client'),
          ),
        );
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Role badge
// ---------------------------------------------------------------------------

class _RoleBadge extends StatelessWidget {
  final String role;

  const _RoleBadge({required this.role});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        role.toUpperCase(),
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: colorScheme.onSecondaryContainer,
        ),
      ),
    );
  }
}
