import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Presence status values for the badge.
enum PresenceStatus {
  available,
  away,
  dnd,
  offline;

  String get label => switch (this) {
        PresenceStatus.available => 'Available',
        PresenceStatus.away => 'Away',
        PresenceStatus.dnd => 'DND',
        PresenceStatus.offline => 'Offline',
      };

  Color get color => switch (this) {
        PresenceStatus.available => AppThemeExtras.statusAvailable,
        PresenceStatus.away => AppThemeExtras.statusAway,
        PresenceStatus.dnd => AppThemeExtras.statusDnd,
        PresenceStatus.offline => AppThemeExtras.statusOffline,
      };

  IconData get icon => switch (this) {
        PresenceStatus.available => Icons.circle,
        PresenceStatus.away => Icons.access_time,
        PresenceStatus.dnd => Icons.do_not_disturb_on,
        PresenceStatus.offline => Icons.circle_outlined,
      };

  static PresenceStatus fromString(String value) => switch (value) {
        'available' => PresenceStatus.available,
        'away' => PresenceStatus.away,
        'dnd' || 'busy' => PresenceStatus.dnd,
        _ => PresenceStatus.offline,
      };
}

/// A small color-coded badge showing a user's presence status.
///
/// Can display as:
/// - Dot only (no text label)
/// - Dot with text label
/// - Pill-shaped badge with icon and label
class StatusBadge extends StatelessWidget {
  final PresenceStatus status;

  /// Whether to show the text label next to the dot.
  final bool showLabel;

  /// Whether to use the pill style (colored background) instead of dot style.
  final bool pill;

  /// Override the font size.
  final double? fontSize;

  const StatusBadge({
    super.key,
    required this.status,
    this.showLabel = false,
    this.pill = false,
    this.fontSize,
  });

  @override
  Widget build(BuildContext context) {
    if (pill) return _buildPill(context);
    return _buildDot(context);
  }

  Widget _buildDot(BuildContext context) {
    final theme = Theme.of(context);
    final effectiveFontSize = fontSize ?? 12.0;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: effectiveFontSize * 0.67,
          height: effectiveFontSize * 0.67,
          decoration: BoxDecoration(
            color: status.color,
            shape: BoxShape.circle,
          ),
        ),
        if (showLabel) ...[
          SizedBox(width: effectiveFontSize * 0.4),
          Text(
            status.label,
            style: theme.textTheme.bodySmall?.copyWith(
              fontSize: effectiveFontSize,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildPill(BuildContext context) {
    final effectiveFontSize = fontSize ?? 11.0;

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: effectiveFontSize * 0.7,
        vertical: effectiveFontSize * 0.2,
      ),
      decoration: BoxDecoration(
        color: status.color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(AppThemeExtras.radiusFull),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            status.icon,
            size: effectiveFontSize,
            color: status.color,
          ),
          SizedBox(width: effectiveFontSize * 0.3),
          Text(
            status.label,
            style: TextStyle(
              fontSize: effectiveFontSize,
              fontWeight: FontWeight.w600,
              color: status.color,
            ),
          ),
        ],
      ),
    );
  }
}
