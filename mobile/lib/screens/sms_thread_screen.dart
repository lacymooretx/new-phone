import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/sms.dart';
import '../providers/sms_provider.dart';

/// SMS thread screen — chat bubble layout for a single conversation.
///
/// Outbound messages are right-aligned (primary color), inbound messages are
/// left-aligned (surface color). Includes a message input bar with TextField
/// and send button. Auto-scrolls to bottom on new messages. Pull up to load
/// older messages.
class SmsThreadScreen extends ConsumerStatefulWidget {
  /// The conversation ID (passed via route parameter).
  final String conversationId;

  const SmsThreadScreen({super.key, required this.conversationId});

  @override
  ConsumerState<SmsThreadScreen> createState() => _SmsThreadScreenState();
}

class _SmsThreadScreenState extends ConsumerState<SmsThreadScreen> {
  final _messageController = TextEditingController();
  final _scrollController = ScrollController();
  final _focusNode = FocusNode();

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _onSend() async {
    final text = _messageController.text.trim();
    if (text.isEmpty) return;

    _messageController.clear();
    await ref.read(smsProvider.notifier).sendMessage(text);
    _scrollToBottom();
  }

  Future<void> _onRefresh() async {
    await ref.read(smsProvider.notifier).refresh();
  }

  @override
  Widget build(BuildContext context) {
    final smsState = ref.watch(smsProvider);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final conversation = smsState.selectedConversation;

    // Auto-scroll when messages change
    ref.listen<SmsState>(smsProvider, (previous, next) {
      if (previous != null &&
          next.messages.length > previous.messages.length) {
        _scrollToBottom();
      }
    });

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              conversation?.remoteNumber ?? 'Messages',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            if (conversation?.didNumber != null &&
                conversation!.didNumber.isNotEmpty)
              Text(
                'via ${conversation.didNumber}',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
          ],
        ),
      ),
      body: Column(
        children: [
          // Messages area
          Expanded(
            child: _buildMessageList(smsState, theme, colorScheme),
          ),

          // Input bar
          _buildInputBar(smsState, theme, colorScheme),
        ],
      ),
    );
  }

  Widget _buildMessageList(
    SmsState smsState,
    ThemeData theme,
    ColorScheme colorScheme,
  ) {
    // Loading state
    if (smsState.isLoadingMessages && smsState.messages.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    // Error state
    if (smsState.error != null && smsState.messages.isEmpty) {
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
              smsState.error!,
              style: theme.textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            FilledButton.tonal(
              onPressed: _onRefresh,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    // Empty state
    if (smsState.messages.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.chat_bubble_outline,
              size: 64,
              color: colorScheme.onSurfaceVariant.withOpacity(0.4),
            ),
            const SizedBox(height: 16),
            Text(
              'No messages yet',
              style: theme.textTheme.titleMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Send a message to start the conversation.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant.withOpacity(0.7),
              ),
            ),
          ],
        ),
      );
    }

    // Message list
    return RefreshIndicator(
      onRefresh: _onRefresh,
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        itemCount: smsState.messages.length,
        itemBuilder: (context, index) {
          final message = smsState.messages[index];

          // Show date separator when the date changes
          final showDateSeparator = index == 0 ||
              !_isSameDay(
                smsState.messages[index - 1].createdAt,
                message.createdAt,
              );

          return Column(
            children: [
              if (showDateSeparator) _DateSeparator(date: message.createdAt),
              _MessageBubble(message: message),
            ],
          );
        },
      ),
    );
  }

  Widget _buildInputBar(
    SmsState smsState,
    ThemeData theme,
    ColorScheme colorScheme,
  ) {
    return Container(
      decoration: BoxDecoration(
        color: colorScheme.surface,
        border: Border(
          top: BorderSide(
            color: colorScheme.outlineVariant,
            width: 0.5,
          ),
        ),
      ),
      padding: EdgeInsets.only(
        left: 12,
        right: 8,
        top: 8,
        bottom: MediaQuery.of(context).padding.bottom + 8,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: TextField(
              controller: _messageController,
              focusNode: _focusNode,
              textCapitalization: TextCapitalization.sentences,
              maxLines: 5,
              minLines: 1,
              decoration: InputDecoration(
                hintText: 'Type a message...',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
                filled: true,
                fillColor: colorScheme.surfaceContainerHighest,
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 10,
                ),
                isDense: true,
              ),
              onSubmitted: (_) => _onSend(),
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(
            width: 40,
            height: 40,
            child: smsState.isSending
                ? const Padding(
                    padding: EdgeInsets.all(8),
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : IconButton(
                    onPressed: _onSend,
                    icon: Icon(
                      Icons.send,
                      color: colorScheme.primary,
                    ),
                    padding: EdgeInsets.zero,
                    tooltip: 'Send',
                  ),
          ),
        ],
      ),
    );
  }

  bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;
}

// ---------------------------------------------------------------------------
// Date separator
// ---------------------------------------------------------------------------

class _DateSeparator extends StatelessWidget {
  final DateTime date;

  const _DateSeparator({required this.date});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Center(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          decoration: BoxDecoration(
            color: colorScheme.surfaceContainerHighest.withOpacity(0.5),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            _formatDate(date),
            style: theme.textTheme.bodySmall?.copyWith(
              color: colorScheme.onSurfaceVariant,
              fontSize: 11,
            ),
          ),
        ),
      ),
    );
  }

  String _formatDate(DateTime dt) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final date = DateTime(dt.year, dt.month, dt.day);

    if (date == today) return 'Today';

    final yesterday = today.subtract(const Duration(days: 1));
    if (date == yesterday) return 'Yesterday';

    final daysAgo = today.difference(date).inDays;
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
      return dayNames[dt.weekday - 1];
    }

    final month = dt.month.toString().padLeft(2, '0');
    final day = dt.day.toString().padLeft(2, '0');
    return '$month/$day/${dt.year}';
  }
}

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------

class _MessageBubble extends StatelessWidget {
  final SmsMessage message;

  const _MessageBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isOutbound = message.isOutbound;

    return Align(
      alignment: isOutbound ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        margin: const EdgeInsets.symmetric(vertical: 3),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isOutbound
              ? colorScheme.primary
              : colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: isOutbound
                ? const Radius.circular(16)
                : const Radius.circular(4),
            bottomRight: isOutbound
                ? const Radius.circular(4)
                : const Radius.circular(16),
          ),
        ),
        child: Column(
          crossAxisAlignment:
              isOutbound ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            Text(
              message.body,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: isOutbound
                    ? colorScheme.onPrimary
                    : colorScheme.onSurface,
              ),
            ),
            const SizedBox(height: 4),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _formatTime(message.createdAt),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: isOutbound
                        ? colorScheme.onPrimary.withOpacity(0.7)
                        : colorScheme.onSurfaceVariant.withOpacity(0.7),
                    fontSize: 10,
                  ),
                ),
                if (isOutbound) ...[
                  const SizedBox(width: 4),
                  Icon(
                    _statusIcon(message.status),
                    size: 12,
                    color: colorScheme.onPrimary.withOpacity(0.7),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  IconData _statusIcon(String status) {
    switch (status) {
      case 'delivered':
        return Icons.done_all;
      case 'sent':
        return Icons.done;
      case 'failed':
        return Icons.error_outline;
      case 'queued':
      case 'pending':
        return Icons.schedule;
      default:
        return Icons.done;
    }
  }

  String _formatTime(DateTime time) {
    final hour = time.hour;
    final minute = time.minute.toString().padLeft(2, '0');
    final period = hour >= 12 ? 'PM' : 'AM';
    final displayHour = hour == 0 ? 12 : (hour > 12 ? hour - 12 : hour);
    return '$displayHour:$minute $period';
  }
}
