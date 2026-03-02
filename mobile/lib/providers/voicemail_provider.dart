import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/voicemail.dart';
import '../services/voicemail_service.dart';
import 'auth_provider.dart';

// ---------------------------------------------------------------------------
// Service provider
// ---------------------------------------------------------------------------

/// Voicemail service singleton.
final voicemailServiceProvider = Provider<VoicemailService>((ref) {
  final api = ref.watch(apiServiceProvider);
  return VoicemailService(api: api);
});

// ---------------------------------------------------------------------------
// Voicemail state
// ---------------------------------------------------------------------------

/// State for the voicemail screen.
class VoicemailState {
  final List<VoicemailBox> boxes;
  final VoicemailBox? selectedBox;
  final List<VoicemailMessage> messages;
  final bool isLoadingBoxes;
  final bool isLoadingMessages;
  final String? error;

  const VoicemailState({
    this.boxes = const [],
    this.selectedBox,
    this.messages = const [],
    this.isLoadingBoxes = false,
    this.isLoadingMessages = false,
    this.error,
  });

  int get totalUnreadCount =>
      boxes.fold(0, (sum, box) => sum + box.unreadCount);

  VoicemailState copyWith({
    List<VoicemailBox>? boxes,
    VoicemailBox? selectedBox,
    List<VoicemailMessage>? messages,
    bool? isLoadingBoxes,
    bool? isLoadingMessages,
    String? error,
    bool clearError = false,
    bool clearSelectedBox = false,
  }) =>
      VoicemailState(
        boxes: boxes ?? this.boxes,
        selectedBox: clearSelectedBox ? null : (selectedBox ?? this.selectedBox),
        messages: messages ?? this.messages,
        isLoadingBoxes: isLoadingBoxes ?? this.isLoadingBoxes,
        isLoadingMessages: isLoadingMessages ?? this.isLoadingMessages,
        error: clearError ? null : (error ?? this.error),
      );
}

// ---------------------------------------------------------------------------
// Voicemail notifier
// ---------------------------------------------------------------------------

final voicemailProvider =
    StateNotifierProvider<VoicemailNotifier, VoicemailState>((ref) {
  final service = ref.watch(voicemailServiceProvider);
  return VoicemailNotifier(service: service);
});

class VoicemailNotifier extends StateNotifier<VoicemailState> {
  final VoicemailService _service;
  String? _tenantId;

  VoicemailNotifier({required VoicemailService service})
      : _service = service,
        super(const VoicemailState());

  /// Load voicemail boxes and select the first one, then load its messages.
  Future<void> loadBoxes(String tenantId) async {
    _tenantId = tenantId;
    state = state.copyWith(isLoadingBoxes: true, clearError: true);

    try {
      final boxes = await _service.getVoicemailBoxes(tenantId);
      state = state.copyWith(
        boxes: boxes,
        isLoadingBoxes: false,
      );

      // Auto-select the first box and load messages
      if (boxes.isNotEmpty) {
        await selectBox(boxes.first);
      }
    } catch (e) {
      debugPrint('[VoicemailProvider] loadBoxes failed: $e');
      state = state.copyWith(
        isLoadingBoxes: false,
        error: 'Failed to load voicemail boxes.',
      );
    }
  }

  /// Select a voicemail box and load its messages.
  Future<void> selectBox(VoicemailBox box) async {
    final tenantId = _tenantId;
    if (tenantId == null) return;

    state = state.copyWith(
      selectedBox: box,
      isLoadingMessages: true,
      clearError: true,
    );

    try {
      final messages = await _service.getMessages(tenantId, box.id);
      state = state.copyWith(
        messages: messages,
        isLoadingMessages: false,
      );
    } catch (e) {
      debugPrint('[VoicemailProvider] loadMessages failed: $e');
      state = state.copyWith(
        isLoadingMessages: false,
        error: 'Failed to load voicemail messages.',
      );
    }
  }

  /// Refresh the current box's messages.
  Future<void> refresh() async {
    final tenantId = _tenantId;
    final box = state.selectedBox;

    if (tenantId == null) return;

    // Reload boxes first (to update counts)
    try {
      final boxes = await _service.getVoicemailBoxes(tenantId);
      state = state.copyWith(boxes: boxes);

      // If we have a selected box, reload its messages
      if (box != null) {
        // Find the updated version of the selected box
        final updatedBox = boxes.firstWhere(
          (b) => b.id == box.id,
          orElse: () => box,
        );
        final messages = await _service.getMessages(tenantId, updatedBox.id);
        state = state.copyWith(
          selectedBox: updatedBox,
          messages: messages,
        );
      } else if (boxes.isNotEmpty) {
        await selectBox(boxes.first);
      }
    } catch (e) {
      debugPrint('[VoicemailProvider] refresh failed: $e');
      state = state.copyWith(
        error: 'Failed to refresh voicemail.',
      );
    }
  }

  /// Mark a message as listened.
  Future<void> markAsListened(String messageId) async {
    final tenantId = _tenantId;
    final box = state.selectedBox;
    if (tenantId == null || box == null) return;

    try {
      await _service.markAsListened(tenantId, box.id, messageId);

      // Update local state
      final updatedMessages = state.messages.map((msg) {
        if (msg.id == messageId) {
          return msg.copyWith(isListened: true);
        }
        return msg;
      }).toList();

      // Decrement unread count on the box
      final updatedBox = box.copyWith(
        unreadCount: (box.unreadCount - 1).clamp(0, box.messageCount),
      );
      final updatedBoxes = state.boxes.map((b) {
        if (b.id == box.id) return updatedBox;
        return b;
      }).toList();

      state = state.copyWith(
        messages: updatedMessages,
        selectedBox: updatedBox,
        boxes: updatedBoxes,
      );
    } catch (e) {
      debugPrint('[VoicemailProvider] markAsListened failed: $e');
    }
  }

  /// Delete a voicemail message.
  Future<void> deleteMessage(String messageId) async {
    final tenantId = _tenantId;
    final box = state.selectedBox;
    if (tenantId == null || box == null) return;

    try {
      await _service.deleteMessage(tenantId, box.id, messageId);

      // Find the message to check if it was unread
      final deletedMsg = state.messages.firstWhere(
        (m) => m.id == messageId,
      );

      // Remove from local state
      final updatedMessages =
          state.messages.where((msg) => msg.id != messageId).toList();

      // Update box counts
      final unreadDelta = deletedMsg.isListened ? 0 : 1;
      final updatedBox = box.copyWith(
        messageCount: (box.messageCount - 1).clamp(0, box.messageCount),
        unreadCount: (box.unreadCount - unreadDelta).clamp(0, box.unreadCount),
      );
      final updatedBoxes = state.boxes.map((b) {
        if (b.id == box.id) return updatedBox;
        return b;
      }).toList();

      state = state.copyWith(
        messages: updatedMessages,
        selectedBox: updatedBox,
        boxes: updatedBoxes,
      );
    } catch (e) {
      debugPrint('[VoicemailProvider] deleteMessage failed: $e');
      state = state.copyWith(error: 'Failed to delete message.');
    }
  }

  /// Get the audio URL for a recording.
  String? getAudioUrl(String recordingId) {
    final tenantId = _tenantId;
    if (tenantId == null) return null;
    return _service.getAudioUrl(tenantId, recordingId);
  }
}
