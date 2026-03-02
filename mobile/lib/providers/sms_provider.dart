import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/sms.dart';
import '../services/sms_service.dart';
import 'auth_provider.dart';

// ---------------------------------------------------------------------------
// Service provider
// ---------------------------------------------------------------------------

/// SMS service singleton.
final smsServiceProvider = Provider<SmsService>((ref) {
  final api = ref.watch(apiServiceProvider);
  return SmsService(api: api);
});

// ---------------------------------------------------------------------------
// SMS state
// ---------------------------------------------------------------------------

/// State for the SMS screens.
class SmsState {
  final List<SmsConversation> conversations;
  final SmsConversation? selectedConversation;
  final List<SmsMessage> messages;
  final bool isLoadingConversations;
  final bool isLoadingMessages;
  final bool isSending;
  final String? error;

  const SmsState({
    this.conversations = const [],
    this.selectedConversation,
    this.messages = const [],
    this.isLoadingConversations = false,
    this.isLoadingMessages = false,
    this.isSending = false,
    this.error,
  });

  int get totalUnreadCount =>
      conversations.fold(0, (sum, c) => sum + c.unreadCount);

  SmsState copyWith({
    List<SmsConversation>? conversations,
    SmsConversation? selectedConversation,
    List<SmsMessage>? messages,
    bool? isLoadingConversations,
    bool? isLoadingMessages,
    bool? isSending,
    String? error,
    bool clearError = false,
    bool clearSelectedConversation = false,
  }) =>
      SmsState(
        conversations: conversations ?? this.conversations,
        selectedConversation: clearSelectedConversation
            ? null
            : (selectedConversation ?? this.selectedConversation),
        messages: messages ?? this.messages,
        isLoadingConversations:
            isLoadingConversations ?? this.isLoadingConversations,
        isLoadingMessages: isLoadingMessages ?? this.isLoadingMessages,
        isSending: isSending ?? this.isSending,
        error: clearError ? null : (error ?? this.error),
      );
}

// ---------------------------------------------------------------------------
// SMS notifier
// ---------------------------------------------------------------------------

final smsProvider =
    StateNotifierProvider<SmsNotifier, SmsState>((ref) {
  final service = ref.watch(smsServiceProvider);
  return SmsNotifier(service: service);
});

class SmsNotifier extends StateNotifier<SmsState> {
  final SmsService _service;
  String? _tenantId;

  SmsNotifier({required SmsService service})
      : _service = service,
        super(const SmsState());

  /// Load SMS conversations for the given tenant.
  Future<void> loadConversations(String tenantId) async {
    _tenantId = tenantId;
    state = state.copyWith(isLoadingConversations: true, clearError: true);

    try {
      final conversations = await _service.getConversations(tenantId);
      state = state.copyWith(
        conversations: conversations,
        isLoadingConversations: false,
      );
    } catch (e) {
      debugPrint('[SmsProvider] loadConversations failed: $e');
      state = state.copyWith(
        isLoadingConversations: false,
        error: 'Failed to load conversations.',
      );
    }
  }

  /// Select a conversation and load its messages.
  Future<void> selectConversation(SmsConversation conversation) async {
    final tenantId = _tenantId;
    if (tenantId == null) return;

    state = state.copyWith(
      selectedConversation: conversation,
      isLoadingMessages: true,
      clearError: true,
    );

    try {
      final messages =
          await _service.getMessages(tenantId, conversation.id);
      state = state.copyWith(
        messages: messages,
        isLoadingMessages: false,
      );
    } catch (e) {
      debugPrint('[SmsProvider] loadMessages failed: $e');
      state = state.copyWith(
        isLoadingMessages: false,
        error: 'Failed to load messages.',
      );
    }
  }

  /// Send a message in the currently selected conversation.
  Future<void> sendMessage(String body) async {
    final tenantId = _tenantId;
    final conversation = state.selectedConversation;
    if (tenantId == null || conversation == null) return;

    state = state.copyWith(isSending: true, clearError: true);

    try {
      final newMessage =
          await _service.sendMessage(tenantId, conversation.id, body);

      // Append the new message to the local list
      final updatedMessages = [...state.messages, newMessage];

      // Update conversation preview
      final updatedConversation = conversation.copyWith(
        lastMessagePreview: body,
        lastMessageAt: newMessage.createdAt,
      );

      // Update conversation in the list
      final updatedConversations = state.conversations.map((c) {
        if (c.id == conversation.id) return updatedConversation;
        return c;
      }).toList();

      state = state.copyWith(
        messages: updatedMessages,
        selectedConversation: updatedConversation,
        conversations: updatedConversations,
        isSending: false,
      );
    } catch (e) {
      debugPrint('[SmsProvider] sendMessage failed: $e');
      state = state.copyWith(
        isSending: false,
        error: 'Failed to send message.',
      );
    }
  }

  /// Refresh conversations and (if selected) current messages.
  Future<void> refresh() async {
    final tenantId = _tenantId;
    final conversation = state.selectedConversation;

    if (tenantId == null) return;

    try {
      final conversations = await _service.getConversations(tenantId);
      state = state.copyWith(conversations: conversations);

      // If we have a selected conversation, reload its messages
      if (conversation != null) {
        final updatedConversation = conversations.firstWhere(
          (c) => c.id == conversation.id,
          orElse: () => conversation,
        );
        final messages =
            await _service.getMessages(tenantId, updatedConversation.id);
        state = state.copyWith(
          selectedConversation: updatedConversation,
          messages: messages,
        );
      }
    } catch (e) {
      debugPrint('[SmsProvider] refresh failed: $e');
      state = state.copyWith(
        error: 'Failed to refresh conversations.',
      );
    }
  }
}
