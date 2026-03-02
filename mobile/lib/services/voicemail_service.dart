import '../models/voicemail.dart';
import 'api_service.dart';

/// Service for voicemail API operations.
///
/// All methods are tenant-scoped. The tenant ID comes from the
/// authenticated user's JWT claims.
class VoicemailService {
  final ApiService _api;

  VoicemailService({required ApiService api}) : _api = api;

  /// Fetch all voicemail boxes for the given tenant.
  Future<List<VoicemailBox>> getVoicemailBoxes(String tenantId) async {
    final response = await _api.get<Map<String, dynamic>>(
      '/tenants/$tenantId/voicemail-boxes',
    );

    final data = response.data!;
    final items = data['items'] as List<dynamic>? ?? data['data'] as List<dynamic>? ?? [];
    return items
        .map((e) => VoicemailBox.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Fetch messages for a specific voicemail box.
  ///
  /// If [unreadOnly] is true, only unread (not listened) messages are returned.
  Future<List<VoicemailMessage>> getMessages(
    String tenantId,
    String boxId, {
    bool unreadOnly = false,
  }) async {
    final queryParams = <String, dynamic>{};
    if (unreadOnly) {
      queryParams['unread_only'] = true;
    }

    final response = await _api.get<Map<String, dynamic>>(
      '/tenants/$tenantId/voicemail-boxes/$boxId/messages',
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
    );

    final data = response.data!;
    final items = data['items'] as List<dynamic>? ?? data['data'] as List<dynamic>? ?? [];
    return items
        .map((e) => VoicemailMessage.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Mark a voicemail message as listened.
  Future<void> markAsListened(
    String tenantId,
    String boxId,
    String messageId,
  ) async {
    await _api.put(
      '/tenants/$tenantId/voicemail-boxes/$boxId/messages/$messageId',
      data: {'is_listened': true},
    );
  }

  /// Delete a voicemail message.
  Future<void> deleteMessage(
    String tenantId,
    String boxId,
    String messageId,
  ) async {
    await _api.delete(
      '/tenants/$tenantId/voicemail-boxes/$boxId/messages/$messageId',
    );
  }

  /// Construct the audio streaming URL for a recording.
  ///
  /// Returns a full URL that can be passed to an audio player. The caller
  /// must attach an auth header separately (the URL itself does not embed
  /// the token for security reasons).
  String getAudioUrl(String tenantId, String recordingId) {
    final baseUrl = _api.dio.options.baseUrl;
    return '$baseUrl/tenants/$tenantId/recordings/$recordingId/audio';
  }
}
