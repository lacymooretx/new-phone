import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

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
            subtitle: const Text('Default'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Ringtone selection coming soon')),
              );
            },
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
            onTap: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Password change coming soon'),
                ),
              );
            },
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
            onTap: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Support page coming soon')),
              );
            },
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
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Profile editing coming soon'),
                    ),
                  );
                },
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
