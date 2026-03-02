import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/sms.dart';
import '../providers/auth_provider.dart';
import '../providers/sms_provider.dart';

/// SMS conversations list screen — shows all SMS conversations.
///
/// Each row displays the remote number, DID number, last message preview,
/// unread badge, and timestamp. Pull to refresh. Tapping a conversation
/// navigates to the thread view.
class SmsConversationsScreen extends ConsumerStatefulWidget {
  const SmsConversationsScreen({super.key});

  @override
  ConsumerState<SmsConversationsScreen> createState() =>
      _SmsConversationsScreenState();
}

class _SmsConversationsScreenState
    extends ConsumerState<SmsConversationsScreen> {
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
      ref
          .read(smsProvider.notifier)
          .loadConversations(authState.user.tenantId);
    }
  }

  Future<void> _onRefresh() async {
    await ref.read(smsProvider.notifier).refresh();
  }

  void _onConversationTap(SmsConversation conversation) {
    ref.read(smsProvider.notifier).selectConversation(conversation);
    context.push('/sms/${conversation.id}');
  }

  @override
  Widget build(BuildContext context) {
    final smsState = ref.watch(smsProvider);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Messages'),
            if (smsState.totalUnreadCount > 0) ...[
              const SizedBox(width: 8),
              _UnreadBadge(count: smsState.totalUnreadCount),
            ],
          ],
        ),
      ),
      body: _buildBody(smsState, theme, colorScheme),
    );
  }

  Widget _buildBody(
    SmsState smsState,
    ThemeData theme,
    ColorScheme colorScheme,
  ) {
    // Loading state
    if (smsState.isLoadingConversations &&
        smsState.conversations.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    // Error state
    if (smsState.error != null && smsState.conversations.isEmpty) {
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
              onPressed: _loadData,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    // Empty state
    if (smsState.conversations.isEmpty) {
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
                      Icons.message_outlined,
                      size: 64,
                      color: colorScheme.onSurfaceVariant.withOpacity(0.4),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'No messages',
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Your SMS conversations will appear here.',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color:
                            colorScheme.onSurfaceVariant.withOpacity(0.7),
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

    // Conversation list
    return RefreshIndicator(
      onRefresh: _onRefresh,
      child: ListView.separated(
        itemCount: smsState.conversations.length,
        separatorBuilder: (context, index) =>
            const Divider(height: 1, indent: 72),
        itemBuilder: (context, index) {
          final conversation = smsState.conversations[index];
          return _ConversationTile(
            conversation: conversation,
            onTap: () => _onConversationTap(conversation),
          );
        },
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Conversation tile
// ---------------------------------------------------------------------------

class _ConversationTile extends StatelessWidget {
  final SmsConversation conversation;
  final VoidCallback onTap;

  const _ConversationTile({
    required this.conversation,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final hasUnread = conversation.unreadCount > 0;

    return ListTile(
      onTap: onTap,
      leading: CircleAvatar(
        backgroundColor: hasUnread
            ? colorScheme.primaryContainer
            : colorScheme.surfaceContainerHighest,
        child: Icon(
          Icons.message,
          color: hasUnread
              ? colorScheme.onPrimaryContainer
              : colorScheme.onSurfaceVariant,
          size: 20,
        ),
      ),
      title: Row(
        children: [
          Expanded(
            child: Text(
              conversation.remoteNumber,
              style: theme.textTheme.bodyLarge?.copyWith(
                fontWeight: hasUnread ? FontWeight.w600 : FontWeight.w400,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (hasUnread)
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
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (conversation.lastMessagePreview != null)
            Text(
              conversation.lastMessagePreview!,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
                fontWeight: hasUnread ? FontWeight.w500 : FontWeight.w400,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          Row(
            children: [
              Text(
                conversation.didNumber,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colorScheme.onSurfaceVariant.withOpacity(0.7),
                  fontSize: 11,
                ),
              ),
              if (conversation.lastMessageAt != null) ...[
                Text(
                  ' \u00b7 ',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurfaceVariant.withOpacity(0.7),
                  ),
                ),
                Text(
                  _formatTime(conversation.lastMessageAt!),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurfaceVariant.withOpacity(0.7),
                    fontSize: 11,
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
      trailing: hasUnread
          ? _UnreadBadge(count: conversation.unreadCount)
          : null,
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
