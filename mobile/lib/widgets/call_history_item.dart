import 'package:flutter/material.dart';

import '../models/cdr.dart';

/// Reusable list tile for a call history record.
///
/// Shows a direction icon with color, caller/called name or number, time
/// (relative for today, date for older), and duration. Invokes [onTap]
/// when pressed.
class CallHistoryItem extends StatelessWidget {
  final Cdr cdr;
  final VoidCallback? onTap;

  const CallHistoryItem({
    super.key,
    required this.cdr,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return ListTile(
      leading: _DirectionIcon(cdr: cdr),
      title: Text(
        cdr.remotePartyLabel,
        style: theme.textTheme.bodyLarge?.copyWith(
          fontWeight: cdr.isMissed ? FontWeight.w600 : FontWeight.w400,
          color: cdr.isMissed ? colorScheme.error : null,
        ),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Text(
        _subtitle(cdr),
        style: theme.textTheme.bodySmall?.copyWith(
          color: colorScheme.onSurfaceVariant,
        ),
      ),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(
            _formatTime(cdr.startTime),
            style: theme.textTheme.bodySmall?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
          ),
          if (cdr.disposition == CdrDisposition.answered && cdr.duration > 0)
            Text(
              cdr.formattedDuration,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant.withOpacity(0.7),
                fontSize: 11,
              ),
            ),
        ],
      ),
      onTap: onTap,
    );
  }

  String _subtitle(Cdr cdr) {
    final parts = <String>[];

    // Direction label
    switch (cdr.direction) {
      case CdrDirection.inbound:
        parts.add('Incoming');
      case CdrDirection.outbound:
        parts.add('Outgoing');
      case CdrDirection.internal:
        parts.add('Internal');
    }

    // Disposition if not answered
    if (cdr.disposition == CdrDisposition.voicemail) {
      parts.add('Voicemail');
    } else if (cdr.disposition == CdrDisposition.busy) {
      parts.add('Busy');
    } else if (cdr.disposition == CdrDisposition.failed) {
      parts.add('Failed');
    }

    // Remote number if we're showing a name
    if (cdr.callerName != null && cdr.direction == CdrDirection.inbound) {
      parts.add(cdr.callerNumber);
    }

    return parts.join(' \u00b7 ');
  }

  /// Format the time display. Shows relative time for today, date for older.
  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final dateOfCall = DateTime(time.year, time.month, time.day);

    if (dateOfCall == today) {
      // Today — show time
      final hour = time.hour;
      final minute = time.minute.toString().padLeft(2, '0');
      final period = hour >= 12 ? 'PM' : 'AM';
      final displayHour = hour == 0 ? 12 : (hour > 12 ? hour - 12 : hour);
      return '$displayHour:$minute $period';
    }

    final yesterday = today.subtract(const Duration(days: 1));
    if (dateOfCall == yesterday) {
      return 'Yesterday';
    }

    // Within this week
    final daysAgo = today.difference(dateOfCall).inDays;
    if (daysAgo < 7) {
      const dayNames = [
        'Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday',
        'Saturday',
        'Sunday',
      ];
      return dayNames[time.weekday - 1];
    }

    // Older — show date
    final month = time.month.toString().padLeft(2, '0');
    final day = time.day.toString().padLeft(2, '0');
    return '${month}/${day}/${time.year}';
  }
}

// ---------------------------------------------------------------------------
// Direction icon
// ---------------------------------------------------------------------------

class _DirectionIcon extends StatelessWidget {
  final Cdr cdr;

  const _DirectionIcon({required this.cdr});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    IconData icon;
    Color color;

    switch (cdr.direction) {
      case CdrDirection.inbound:
        if (cdr.isMissed) {
          icon = Icons.call_missed;
          color = colorScheme.error;
        } else {
          icon = Icons.call_received;
          color = const Color(0xFF4CAF50); // Green
        }

      case CdrDirection.outbound:
        icon = Icons.call_made;
        if (cdr.isMissed) {
          color = colorScheme.error;
        } else {
          color = colorScheme.primary; // Blue
        }

      case CdrDirection.internal:
        icon = Icons.swap_calls;
        color = colorScheme.tertiary;
    }

    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        shape: BoxShape.circle,
      ),
      child: Center(
        child: Icon(icon, color: color, size: 20),
      ),
    );
  }
}
