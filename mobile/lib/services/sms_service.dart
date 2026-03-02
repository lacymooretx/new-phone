import '../models/sms.dart';
import 'api_service.dart';

/// Service for SMS API operations.
///
/// All methods are tenant-scoped. The tenant ID comes from the
/// authenticated user's JWT claims.
class SmsService {
  final ApiService _api;

  SmsService({required ApiService api}) : _api = api;

  /// Fetch SMS conversations for the given tenant.
  ///
  /// Optionally filter by [state] (e.g. 'open', 'closed').
  /// Supports pagination via [page] and [pageSize].
  Future<List<SmsConversation>> getConversations(
    String tenantId, {
    String? state,
    int page = 1,
    int pageSize = 50,
  }) async {
    final queryParams = <String, dynamic>{
      'page': page,
      'page_size': pageSize,
    };
    if (state != null) {
      queryParams['state'] = state;
    }

    final response = await _api.get<Map<String, dynamic>>(
      '/tenants/$tenantId/sms/conversations',
      queryParameters: queryParams,
    );

    final data = response.data!;
    final items =
        data['items'] as List<dynamic>? ?? data['data'] as List<dynamic>? ?? [];
    return items
        .map((e) => SmsConversation.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Fetch messages for a specific conversation.
  ///
  /// Supports pagination via [page] and [pageSize].
  Future<List<SmsMessage>> getMessages(
    String tenantId,
    String conversationId, {
    int page = 1,
    int pageSize = 50,
  }) async {
    final queryParams = <String, dynamic>{
      'page': page,
      'page_size': pageSize,
    };

    final response = await _api.get<Map<String, dynamic>>(
      '/tenants/$tenantId/sms/conversations/$conversationId/messages',
      queryParameters: queryParams,
    );

    final data = response.data!;
    final items =
        data['items'] as List<dynamic>? ?? data['data'] as List<dynamic>? ?? [];
    return items
        .map((e) => SmsMessage.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Send a new message in an existing conversation.
  Future<SmsMessage> sendMessage(
    String tenantId,
    String conversationId,
    String body,
  ) async {
    final response = await _api.post<Map<String, dynamic>>(
      '/tenants/$tenantId/sms/conversations/$conversationId/messages',
      data: {'body': body},
    );

    return SmsMessage.fromJson(response.data!);
  }
}
