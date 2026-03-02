import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Avatar size presets.
enum AvatarSize {
  small(16.0, 12.0, 8.0),
  medium(24.0, 16.0, 10.0),
  large(36.0, 22.0, 12.0),
  xLarge(48.0, 28.0, 14.0);

  /// Radius of the CircleAvatar.
  final double radius;

  /// Font size for initials text.
  final double fontSize;

  /// Size of the status dot.
  final double dotSize;

  const AvatarSize(this.radius, this.fontSize, this.dotSize);
}

/// Reusable avatar widget with initials fallback and optional status dot.
///
/// Displays a circular avatar with:
/// - Initials derived from [name] (or first character of [name] if single word)
/// - Background color deterministically chosen from [name] hash
/// - Optional online/offline status indicator dot
/// - Configurable size via [AvatarSize]
class AvatarWidget extends StatelessWidget {
  /// Full name used to derive initials and background color.
  final String name;

  /// Avatar size preset.
  final AvatarSize size;

  /// Whether to show the status dot.
  final bool showStatus;

  /// Whether the contact is online.
  final bool isOnline;

  /// Status string for dot color ('available', 'away', 'dnd', 'offline').
  /// If null, uses [isOnline] to determine available/offline.
  final String? status;

  /// Optional network image URL for a photo avatar.
  final String? imageUrl;

  const AvatarWidget({
    super.key,
    required this.name,
    this.size = AvatarSize.medium,
    this.showStatus = false,
    this.isOnline = false,
    this.status,
    this.imageUrl,
  });

  @override
  Widget build(BuildContext context) {
    final bgColor = _backgroundColorForName(name, context);
    final fgColor = _foregroundColorForBackground(bgColor);

    return Stack(
      clipBehavior: Clip.none,
      children: [
        CircleAvatar(
          radius: size.radius,
          backgroundColor: bgColor,
          backgroundImage:
              imageUrl != null ? NetworkImage(imageUrl!) : null,
          child: imageUrl == null
              ? Text(
                  _initials(name),
                  style: TextStyle(
                    fontSize: size.fontSize,
                    fontWeight: FontWeight.w600,
                    color: fgColor,
                  ),
                )
              : null,
        ),
        if (showStatus)
          Positioned(
            right: 0,
            bottom: 0,
            child: _StatusDot(
              dotSize: size.dotSize,
              color: _statusColor,
            ),
          ),
      ],
    );
  }

  Color get _statusColor {
    if (status != null) {
      return AppThemeExtras.colorForStatus(status!);
    }
    return isOnline
        ? AppThemeExtras.statusAvailable
        : AppThemeExtras.statusOffline;
  }

  /// Generate initials from a name string.
  static String _initials(String name) {
    final trimmed = name.trim();
    if (trimmed.isEmpty) return '?';

    final parts = trimmed.split(RegExp(r'\s+'));
    if (parts.length >= 2) {
      return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
    }
    return parts.first[0].toUpperCase();
  }

  /// Deterministic background color from name hash.
  ///
  /// Uses a set of muted Material colors that look good with white text.
  static Color _backgroundColorForName(String name, BuildContext context) {
    const colors = [
      Color(0xFF1565C0), // Blue 800
      Color(0xFF2E7D32), // Green 800
      Color(0xFFC62828), // Red 800
      Color(0xFF6A1B9A), // Purple 800
      Color(0xFFE65100), // Orange 900
      Color(0xFF00838F), // Cyan 800
      Color(0xFF4527A0), // Deep Purple 800
      Color(0xFF283593), // Indigo 800
      Color(0xFF558B2F), // Light Green 800
      Color(0xFF880E4F), // Pink 900
      Color(0xFF00695C), // Teal 800
      Color(0xFF4E342E), // Brown 800
    ];

    final hash = name.hashCode.abs();
    return colors[hash % colors.length];
  }

  /// Choose white or dark text depending on background brightness.
  static Color _foregroundColorForBackground(Color bg) {
    // Use relative luminance to decide
    final luminance = bg.computeLuminance();
    return luminance > 0.4 ? Colors.black87 : Colors.white;
  }
}

/// Small colored dot indicating online/presence status.
class _StatusDot extends StatelessWidget {
  final double dotSize;
  final Color color;

  const _StatusDot({
    required this.dotSize,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final borderColor = Theme.of(context).colorScheme.surface;

    return Container(
      width: dotSize,
      height: dotSize,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(
          color: borderColor,
          width: dotSize * 0.15,
        ),
      ),
    );
  }
}
