import '../models/contact.dart';
import 'api_service.dart';

/// Service for company directory / extensions API operations.
///
/// All methods are tenant-scoped. The tenant ID comes from the
/// authenticated user's JWT claims.
class ContactsService {
  final ApiService _api;

  ContactsService({required ApiService api}) : _api = api;

  /// Fetch the company directory (extensions with user info).
  ///
  /// Optionally filter by [search] (matches name, extension number, email).
  Future<List<Contact>> getContacts(
    String tenantId, {
    String? search,
  }) async {
    final queryParams = <String, dynamic>{};
    if (search != null && search.isNotEmpty) {
      queryParams['search'] = search;
    }

    final response = await _api.get<Map<String, dynamic>>(
      '/tenants/$tenantId/extensions',
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
    );

    final data = response.data!;
    final items = data['items'] as List<dynamic>? ??
        data['data'] as List<dynamic>? ??
        [];
    return items
        .map((e) => Contact.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Fetch a single contact by extension ID.
  Future<Contact> getContact(String tenantId, String extensionId) async {
    final response = await _api.get<Map<String, dynamic>>(
      '/tenants/$tenantId/extensions/$extensionId',
    );

    return Contact.fromJson(response.data!);
  }
}
