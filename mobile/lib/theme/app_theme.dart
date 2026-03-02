import 'package:flutter/material.dart';

/// Enhanced application theme with call-state colors, spacing tokens,
/// and typography scale.
///
/// This supplements the base theme in `config/theme.dart` with semantic
/// color constants and layout tokens used across the app.
class AppThemeExtras {
  AppThemeExtras._();

  // ---------------------------------------------------------------------------
  // Call state colors
  // ---------------------------------------------------------------------------

  /// Green — connected call, available status, success.
  static const Color callConnected = Color(0xFF4CAF50);

  /// Red — ended call, error, missed, DND.
  static const Color callEnded = Color(0xFFF44336);

  /// Yellow/Amber — ringing, away status.
  static const Color callRinging = Color(0xFFFFC107);

  /// Orange — hold state, warning.
  static const Color callOnHold = Color(0xFFFF9800);

  // ---------------------------------------------------------------------------
  // Status colors
  // ---------------------------------------------------------------------------

  /// Online / available.
  static const Color statusAvailable = Color(0xFF4CAF50);

  /// Away / idle.
  static const Color statusAway = Color(0xFFFFC107);

  /// Do not disturb / busy.
  static const Color statusDnd = Color(0xFFF44336);

  /// Offline / unavailable.
  static const Color statusOffline = Color(0xFF9E9E9E);

  /// Get the color for a given status string.
  static Color colorForStatus(String status) => switch (status) {
        'available' => statusAvailable,
        'away' => statusAway,
        'dnd' || 'busy' => statusDnd,
        _ => statusOffline,
      };

  // ---------------------------------------------------------------------------
  // Spacing tokens
  // ---------------------------------------------------------------------------

  /// Extra-small spacing (4px).
  static const double spaceXs = 4.0;

  /// Small spacing (8px).
  static const double spaceSm = 8.0;

  /// Medium spacing (16px).
  static const double spaceMd = 16.0;

  /// Large spacing (24px).
  static const double spaceLg = 24.0;

  /// Extra-large spacing (32px).
  static const double spaceXl = 32.0;

  /// 2x extra-large spacing (48px).
  static const double spaceXxl = 48.0;

  // ---------------------------------------------------------------------------
  // Radius tokens
  // ---------------------------------------------------------------------------

  /// Small radius for chips, badges (8px).
  static const double radiusSm = 8.0;

  /// Medium radius for cards, inputs (12px).
  static const double radiusMd = 12.0;

  /// Large radius for sheets, dialogs (16px).
  static const double radiusLg = 16.0;

  /// Full radius for circular elements.
  static const double radiusFull = 999.0;

  // ---------------------------------------------------------------------------
  // Icon sizes
  // ---------------------------------------------------------------------------

  /// Small icon size (16px).
  static const double iconSm = 16.0;

  /// Medium icon size (24px).
  static const double iconMd = 24.0;

  /// Large icon size (32px).
  static const double iconLg = 32.0;

  /// Extra-large icon size (48px).
  static const double iconXl = 48.0;

  // ---------------------------------------------------------------------------
  // Avatar sizes
  // ---------------------------------------------------------------------------

  /// Small avatar radius (16px diameter = 32px).
  static const double avatarSmall = 16.0;

  /// Medium avatar radius (24px diameter = 48px).
  static const double avatarMedium = 24.0;

  /// Large avatar radius (36px diameter = 72px).
  static const double avatarLarge = 36.0;

  /// Extra-large avatar radius (48px diameter = 96px).
  static const double avatarXLarge = 48.0;

  // ---------------------------------------------------------------------------
  // Typography helpers
  // ---------------------------------------------------------------------------

  /// Section header text style.
  static TextStyle sectionHeader(BuildContext context) {
    final theme = Theme.of(context);
    return theme.textTheme.labelLarge!.copyWith(
      color: theme.colorScheme.onSurfaceVariant,
      fontWeight: FontWeight.w600,
      letterSpacing: 0.5,
    );
  }

  /// Settings item title style.
  static TextStyle settingsTitle(BuildContext context) {
    final theme = Theme.of(context);
    return theme.textTheme.bodyLarge!;
  }

  /// Settings item subtitle style.
  static TextStyle settingsSubtitle(BuildContext context) {
    final theme = Theme.of(context);
    return theme.textTheme.bodySmall!.copyWith(
      color: theme.colorScheme.onSurfaceVariant,
    );
  }
}
