import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/cdr.dart';
import '../providers/auth_provider.dart';
import '../providers/call_provider.dart';
import '../services/cdr_service.dart';

/// Contact / extension detail screen.
///
/// Shows contact info (name, number, email), action buttons (Call, Message,
/// Voicemail), and recent call history with this contact. Accessible by
/// tapping a call record in the call history.
class ContactDetailScreen extends ConsumerStatefulWidget {
  /// The phone number / extension of the contact.
  final String phoneNumber;

  /// Optional CDR passed via route extra to pre-populate info.
  final Cdr? initialCdr;

  const ContactDetailScreen({
    super.key,
    required this.phoneNumber,
    this.initialCdr,
  });

  @override
  ConsumerState<ContactDetailScreen> createState() =>
      _ContactDetailScreenState();
}

class _ContactDetailScreenState extends ConsumerState<ContactDetailScreen> {
  List<Cdr> _recentCalls = [];
  bool _isLoading = true;
  String? _error;

  /// Resolved display name from CDR or number.
  String get _displayName =>
      widget.initialCdr?.callerName ?? widget.phoneNumber;

  @override
  void initState() {
    super.initState();
    _loadRecentCalls();
  }

  Future<void> _loadRecentCalls() async {
    final authState = ref.read(authProvider);
    if (authState is! AuthAuthenticated) return;

    final apiService = ref.read(apiServiceProvider);
    final cdrService = CdrService(api: apiService);

    try {
      final page = await cdrService.getCdrs(
        authState.user.tenantId,
        search: widget.phoneNumber,
        pageSize: 20,
      );
      if (mounted) {
        setState(() {
          _recentCalls = page.items;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Failed to load call history.';
          _isLoading = false;
        });
      }
    }
  }

  void _onCall() {
    HapticFeedback.mediumImpact();
    ref.read(callProvider.notifier).makeCall(widget.phoneNumber);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    // Navigate on call state changes
    ref.listen<CallState>(callProvider, (previous, next) {
      if (next is CallConnecting || next is CallConnected) {
        context.go('/call/active');
      }
    });

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('Contact'),
      ),
      body: ListView(
        children: [
          const SizedBox(height: 24),

          // Avatar and name
          Center(
            child: Column(
              children: [
                CircleAvatar(
                  radius: 40,
                  backgroundColor: colorScheme.primaryContainer,
                  child: Text(
                    _initials(_displayName),
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      color: colorScheme.onPrimaryContainer,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  _displayName,
                  style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  widget.phoneNumber,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
                if (widget.initialCdr != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    _directionLabel(widget.initialCdr!),
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant.withOpacity(0.7),
                    ),
                  ),
                ],
              ],
            ),
          ),

          const SizedBox(height: 24),

          // Action buttons
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 48),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _ActionButton(
                  icon: Icons.call,
                  label: 'Call',
                  color: const Color(0xFF4CAF50),
                  onPressed: _onCall,
                ),
                _ActionButton(
                  icon: Icons.message_outlined,
                  label: 'Message',
                  color: colorScheme.primary,
                  onPressed: () {
                    // TODO: Navigate to messaging / SMS screen
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Messaging coming soon')),
                    );
                  },
                ),
                _ActionButton(
                  icon: Icons.voicemail_outlined,
                  label: 'Voicemail',
                  color: colorScheme.tertiary,
                  onPressed: () {
                    // TODO: Navigate to voicemail for this contact
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Direct voicemail coming soon'),
                      ),
                    );
                  },
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),
          const Divider(),

          // Recent call history with this contact
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text(
              'Recent Calls',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
          ),

          if (_isLoading)
            const Padding(
              padding: EdgeInsets.all(32),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_error != null)
            Padding(
              padding: const EdgeInsets.all(32),
              child: Center(
                child: Text(
                  _error!,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: colorScheme.error,
                  ),
                ),
              ),
            )
          else if (_recentCalls.isEmpty)
            Padding(
              padding: const EdgeInsets.all(32),
              child: Center(
                child: Text(
                  'No call history with this contact.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
            )
          else
            ..._recentCalls.map(
              (cdr) => _RecentCallTile(cdr: cdr),
            ),

          const SizedBox(height: 24),
        ],
      ),
    );
  }

  String _initials(String text) {
    final parts = text.trim().split(RegExp(r'\s+'));
    if (parts.length >= 2) {
      return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
    }
    if (text.isNotEmpty) {
      return text[0].toUpperCase();
    }
    return '?';
  }

  String _directionLabel(Cdr cdr) {
    switch (cdr.direction) {
      case CdrDirection.inbound:
        return 'Last call: Incoming';
      case CdrDirection.outbound:
        return 'Last call: Outgoing';
      case CdrDirection.internal:
        return 'Last call: Internal';
    }
  }
}

// ---------------------------------------------------------------------------
// Action button
// ---------------------------------------------------------------------------

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onPressed;

  const _ActionButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 56,
          height: 56,
          child: Material(
            color: color.withOpacity(0.1),
            shape: const CircleBorder(),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onTap: onPressed,
              customBorder: const CircleBorder(),
              child: Center(
                child: Icon(icon, color: color, size: 24),
              ),
            ),
          ),
        ),
        const SizedBox(height: 6),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: color,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Recent call tile
// ---------------------------------------------------------------------------

class _RecentCallTile extends StatelessWidget {
  final Cdr cdr;

  const _RecentCallTile({required this.cdr});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    IconData icon;
    Color iconColor;

    switch (cdr.direction) {
      case CdrDirection.inbound:
        if (cdr.isMissed) {
          icon = Icons.call_missed;
          iconColor = colorScheme.error;
        } else {
          icon = Icons.call_received;
          iconColor = const Color(0xFF4CAF50);
        }
      case CdrDirection.outbound:
        icon = Icons.call_made;
        iconColor = cdr.isMissed ? colorScheme.error : colorScheme.primary;
      case CdrDirection.internal:
        icon = Icons.swap_calls;
        iconColor = colorScheme.tertiary;
    }

    return ListTile(
      leading: Icon(icon, color: iconColor, size: 20),
      title: Text(
        _directionText(cdr),
        style: theme.textTheme.bodyMedium?.copyWith(
          color: cdr.isMissed ? colorScheme.error : null,
        ),
      ),
      subtitle: Text(
        _formatDateTime(cdr.startTime),
        style: theme.textTheme.bodySmall?.copyWith(
          color: colorScheme.onSurfaceVariant,
        ),
      ),
      trailing: cdr.disposition == CdrDisposition.answered && cdr.duration > 0
          ? Text(
              cdr.formattedDuration,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            )
          : null,
    );
  }

  String _directionText(Cdr cdr) {
    final direction = switch (cdr.direction) {
      CdrDirection.inbound => 'Incoming',
      CdrDirection.outbound => 'Outgoing',
      CdrDirection.internal => 'Internal',
    };

    if (cdr.isMissed) return '$direction (Missed)';
    if (cdr.disposition == CdrDisposition.voicemail) {
      return '$direction (Voicemail)';
    }
    if (cdr.disposition == CdrDisposition.busy) return '$direction (Busy)';

    return direction;
  }

  String _formatDateTime(DateTime dt) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final date = DateTime(dt.year, dt.month, dt.day);

    final hour = dt.hour;
    final minute = dt.minute.toString().padLeft(2, '0');
    final period = hour >= 12 ? 'PM' : 'AM';
    final displayHour = hour == 0 ? 12 : (hour > 12 ? hour - 12 : hour);
    final timeStr = '$displayHour:$minute $period';

    if (date == today) return 'Today $timeStr';

    final yesterday = today.subtract(const Duration(days: 1));
    if (date == yesterday) return 'Yesterday $timeStr';

    final month = dt.month.toString().padLeft(2, '0');
    final day = dt.day.toString().padLeft(2, '0');
    return '$month/$day/${dt.year} $timeStr';
  }
}
