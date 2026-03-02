import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/voicemail.dart';
import '../providers/auth_provider.dart';
import '../providers/voicemail_provider.dart';
import '../widgets/voicemail_player.dart';

/// Voicemail screen — replaces the placeholder VoicemailTab.
///
/// Lists voicemail messages grouped by date. Each message shows caller info,
/// time, duration, and an unread indicator. Tapping a message expands it to
/// show playback controls and transcription. Swipe to delete with confirmation.
/// Pull to refresh. Badge showing unread count.
class VoicemailScreen extends ConsumerStatefulWidget {
  const VoicemailScreen({super.key});

  @override
  ConsumerState<VoicemailScreen> createState() => _VoicemailScreenState();
}

class _VoicemailScreenState extends ConsumerState<VoicemailScreen> {
  String? _expandedMessageId;
  bool _initialized = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_initialized) {
      _initialized = true;
      _loadData();
    }
  }

  void _loadData() {
    final authState = ref.read(authProvider);
    if (authState is AuthAuthenticated) {
      ref.read(voicemailProvider.notifier).loadBoxes(authState.user.tenantId);
    }
  }

  Future<void> _onRefresh() async {
    await ref.read(voicemailProvider.notifier).refresh();
  }

  void _toggleExpand(String messageId) {
    setState(() {
      if (_expandedMessageId == messageId) {
        _expandedMessageId = null;
      } else {
        _expandedMessageId = messageId;
      }
    });
  }

  Future<void> _onDelete(VoicemailMessage message) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Voicemail'),
        content: Text(
          'Delete voicemail from ${message.callerLabel}?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      await ref.read(voicemailProvider.notifier).deleteMessage(message.id);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Voicemail deleted')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final vmState = ref.watch(voicemailProvider);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Voicemail'),
            if (vmState.totalUnreadCount > 0) ...[
              const SizedBox(width: 8),
              _UnreadBadge(count: vmState.totalUnreadCount),
            ],
          ],
        ),
        actions: [
          // Box selector if multiple boxes
          if (vmState.boxes.length > 1)
            PopupMenuButton<VoicemailBox>(
              onSelected: (box) {
                ref.read(voicemailProvider.notifier).selectBox(box);
              },
              icon: const Icon(Icons.inbox_outlined),
              itemBuilder: (context) => vmState.boxes
                  .map(
                    (box) => PopupMenuItem<VoicemailBox>(
                      value: box,
                      child: Row(
                        children: [
                          if (box.id == vmState.selectedBox?.id)
                            Icon(Icons.check, size: 16, color: colorScheme.primary)
                          else
                            const SizedBox(width: 16),
                          const SizedBox(width: 8),
                          Expanded(child: Text(box.name)),
                          if (box.unreadCount > 0)
                            _UnreadBadge(count: box.unreadCount),
                        ],
                      ),
                    ),
                  )
                  .toList(),
            ),
        ],
      ),
      body: _buildBody(vmState, theme, colorScheme),
    );
  }

  Widget _buildBody(
    VoicemailState vmState,
    ThemeData theme,
    ColorScheme colorScheme,
  ) {
    // Loading state
    if (vmState.isLoadingBoxes ||
        (vmState.isLoadingMessages && vmState.messages.isEmpty)) {
      return const Center(child: CircularProgressIndicator());
    }

    // Error state
    if (vmState.error != null && vmState.messages.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline,
              size: 48,
              color: colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              vmState.error!,
              style: theme.textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            FilledButton.tonal(
              onPressed: _loadData,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    // Empty state
    if (vmState.messages.isEmpty) {
      return RefreshIndicator(
        onRefresh: _onRefresh,
        child: ListView(
          children: [
            SizedBox(
              height: MediaQuery.of(context).size.height * 0.6,
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.voicemail_outlined,
                      size: 64,
                      color: colorScheme.onSurfaceVariant.withOpacity(0.4),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'No voicemail',
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Your voicemail messages will appear here.',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: colorScheme.onSurfaceVariant.withOpacity(0.7),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
    }

    // Message list grouped by date
    final grouped = _groupByDate(vmState.messages);

    return RefreshIndicator(
      onRefresh: _onRefresh,
      child: ListView.builder(
        itemCount: _totalItemCount(grouped),
        itemBuilder: (context, index) {
          final item = _itemAtIndex(grouped, index);

          // Date header
          if (item is _DateHeader) {
            return Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
              child: Text(
                item.label,
                style: theme.textTheme.labelLarge?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                  fontWeight: FontWeight.w600,
                ),
              ),
            );
          }

          // Voicemail message
          final message = (item as _MessageItem).message;
          final isExpanded = _expandedMessageId == message.id;

          return Dismissible(
            key: Key(message.id),
            direction: DismissDirection.endToStart,
            confirmDismiss: (_) async {
              await _onDelete(message);
              return false; // We handle removal in _onDelete
            },
            background: Container(
              color: colorScheme.error,
              alignment: Alignment.centerRight,
              padding: const EdgeInsets.only(right: 24),
              child: const Icon(Icons.delete_outline, color: Colors.white),
            ),
            child: _VoicemailMessageTile(
              message: message,
              isExpanded: isExpanded,
              onTap: () => _toggleExpand(message.id),
              onListened: () {
                if (!message.isListened) {
                  ref
                      .read(voicemailProvider.notifier)
                      .markAsListened(message.id);
                }
              },
              audioUrl: message.recordingId != null
                  ? ref
                      .read(voicemailProvider.notifier)
                      .getAudioUrl(message.recordingId!)
                  : null,
              authToken: _getAuthToken(),
            ),
          );
        },
      ),
    );
  }

  String? _getAuthToken() {
    final authState = ref.read(authProvider);
    if (authState is AuthAuthenticated) {
      return authState.tokens.accessToken;
    }
    return null;
  }

  // ---------------------------------------------------------------------------
  // Date grouping helpers
  // ---------------------------------------------------------------------------

  Map<String, List<VoicemailMessage>> _groupByDate(
    List<VoicemailMessage> messages,
  ) {
    final grouped = <String, List<VoicemailMessage>>{};

    for (final msg in messages) {
      final label = _dateLabel(msg.createdAt);
      grouped.putIfAbsent(label, () => []).add(msg);
    }

    return grouped;
  }

  String _dateLabel(DateTime dt) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final date = DateTime(dt.year, dt.month, dt.day);

    if (date == today) return 'Today';
    if (date == today.subtract(const Duration(days: 1))) return 'Yesterday';

    final daysAgo = today.difference(date).inDays;
    if (daysAgo < 7) return 'This Week';

    final month = dt.month.toString().padLeft(2, '0');
    final day = dt.day.toString().padLeft(2, '0');
    return '$month/$day/${dt.year}';
  }

  int _totalItemCount(Map<String, List<VoicemailMessage>> grouped) {
    int count = 0;
    for (final entry in grouped.entries) {
      count += 1 + entry.value.length; // header + messages
    }
    return count;
  }

  Object _itemAtIndex(Map<String, List<VoicemailMessage>> grouped, int index) {
    int current = 0;
    for (final entry in grouped.entries) {
      if (current == index) return _DateHeader(entry.key);
      current++;
      for (final msg in entry.value) {
        if (current == index) return _MessageItem(msg);
        current++;
      }
    }
    throw RangeError('Index $index out of range');
  }
}

// ---------------------------------------------------------------------------
// Date header / message item markers
// ---------------------------------------------------------------------------

class _DateHeader {
  final String label;
  const _DateHeader(this.label);
}

class _MessageItem {
  final VoicemailMessage message;
  const _MessageItem(this.message);
}

// ---------------------------------------------------------------------------
// Voicemail message tile
// ---------------------------------------------------------------------------

class _VoicemailMessageTile extends StatelessWidget {
  final VoicemailMessage message;
  final bool isExpanded;
  final VoidCallback onTap;
  final VoidCallback onListened;
  final String? audioUrl;
  final String? authToken;

  const _VoicemailMessageTile({
    required this.message,
    required this.isExpanded,
    required this.onTap,
    required this.onListened,
    this.audioUrl,
    this.authToken,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Column(
      children: [
        ListTile(
          onTap: onTap,
          leading: CircleAvatar(
            backgroundColor: message.isListened
                ? colorScheme.surfaceContainerHighest
                : colorScheme.primaryContainer,
            child: Icon(
              Icons.voicemail,
              color: message.isListened
                  ? colorScheme.onSurfaceVariant
                  : colorScheme.onPrimaryContainer,
              size: 20,
            ),
          ),
          title: Row(
            children: [
              Expanded(
                child: Text(
                  message.callerLabel,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    fontWeight:
                        message.isListened ? FontWeight.w400 : FontWeight.w600,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (!message.isListened)
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: colorScheme.primary,
                    shape: BoxShape.circle,
                  ),
                ),
            ],
          ),
          subtitle: Text(
            '${message.formattedDuration} \u00b7 ${_formatTime(message.createdAt)}',
            style: theme.textTheme.bodySmall?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
          ),
          trailing: Icon(
            isExpanded ? Icons.expand_less : Icons.expand_more,
            color: colorScheme.onSurfaceVariant,
          ),
        ),

        // Expanded content: player and transcription
        if (isExpanded)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Audio player
                if (audioUrl != null)
                  VoicemailPlayer(
                    audioUrl: audioUrl!,
                    durationSeconds: message.duration,
                    authToken: authToken,
                    onListened: onListened,
                  )
                else
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: colorScheme.surfaceContainerHighest.withOpacity(0.3),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          Icons.audio_file,
                          color: colorScheme.onSurfaceVariant,
                          size: 20,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'No recording available',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),

                // Transcription
                if (message.hasTranscription &&
                    message.transcription != null) ...[
                  const SizedBox(height: 12),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: colorScheme.surfaceContainerHighest.withOpacity(0.3),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              Icons.text_snippet_outlined,
                              size: 16,
                              color: colorScheme.onSurfaceVariant,
                            ),
                            const SizedBox(width: 4),
                            Text(
                              'Transcription',
                              style: theme.textTheme.labelSmall?.copyWith(
                                color: colorScheme.onSurfaceVariant,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          message.transcription!,
                          style: theme.textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),

        const Divider(height: 1, indent: 72),
      ],
    );
  }

  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final dateOfMsg = DateTime(time.year, time.month, time.day);

    if (dateOfMsg == today) {
      final hour = time.hour;
      final minute = time.minute.toString().padLeft(2, '0');
      final period = hour >= 12 ? 'PM' : 'AM';
      final displayHour = hour == 0 ? 12 : (hour > 12 ? hour - 12 : hour);
      return '$displayHour:$minute $period';
    }

    final yesterday = today.subtract(const Duration(days: 1));
    if (dateOfMsg == yesterday) {
      return 'Yesterday';
    }

    final month = time.month.toString().padLeft(2, '0');
    final day = time.day.toString().padLeft(2, '0');
    return '$month/$day';
  }
}

// ---------------------------------------------------------------------------
// Unread badge
// ---------------------------------------------------------------------------

class _UnreadBadge extends StatelessWidget {
  final int count;

  const _UnreadBadge({required this.count});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: colorScheme.error,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(
        count > 99 ? '99+' : count.toString(),
        style: const TextStyle(
          color: Colors.white,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
