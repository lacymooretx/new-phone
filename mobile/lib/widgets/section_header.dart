import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Settings section header with a title and optional trailing action.
///
/// Used in settings screens and other list-based layouts to visually
/// separate groups of related items.
class SectionHeader extends StatelessWidget {
  /// Section title text.
  final String title;

  /// Optional widget shown on the trailing end (e.g. a TextButton or Icon).
  final Widget? trailing;

  /// Padding around the header.
  final EdgeInsetsGeometry padding;

  const SectionHeader({
    super.key,
    required this.title,
    this.trailing,
    this.padding = const EdgeInsets.fromLTRB(16, 24, 16, 8),
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: padding,
      child: Row(
        children: [
          Expanded(
            child: Text(
              title.toUpperCase(),
              style: AppThemeExtras.sectionHeader(context),
            ),
          ),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}
