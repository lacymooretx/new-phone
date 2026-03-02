import '../models/cdr.dart';
import 'api_service.dart';

/// Service for Call Detail Record (CDR) API operations.
///
/// All methods are tenant-scoped. The tenant ID comes from the
/// authenticated user's JWT claims.
class CdrService {
  final ApiService _api;

  CdrService({required ApiService api}) : _api = api;

  /// Fetch a paginated list of CDRs with optional filters.
  ///
  /// Parameters:
  /// - [direction]: Filter by call direction ('inbound', 'outbound', 'internal')
  /// - [disposition]: Filter by call disposition ('answered', 'missed', etc.)
  /// - [startDate]: Include only calls on or after this date
  /// - [endDate]: Include only calls on or before this date
  /// - [search]: Free-text search across caller/called number and name
  /// - [page]: Page number (1-based)
  /// - [pageSize]: Number of records per page
  Future<CdrPage> getCdrs(
    String tenantId, {
    String? direction,
    String? disposition,
    DateTime? startDate,
    DateTime? endDate,
    String? search,
    int page = 1,
    int pageSize = 50,
  }) async {
    final queryParams = <String, dynamic>{
      'page': page,
      'page_size': pageSize,
    };

    if (direction != null) queryParams['direction'] = direction;
    if (disposition != null) queryParams['disposition'] = disposition;
    if (startDate != null) {
      queryParams['start_date'] = startDate.toIso8601String();
    }
    if (endDate != null) {
      queryParams['end_date'] = endDate.toIso8601String();
    }
    if (search != null && search.isNotEmpty) {
      queryParams['search'] = search;
    }

    final response = await _api.get<Map<String, dynamic>>(
      '/tenants/$tenantId/cdrs',
      queryParameters: queryParams,
    );

    return CdrPage.fromJson(response.data!);
  }

  /// Fetch a single CDR by ID.
  Future<Cdr> getCdr(String tenantId, String cdrId) async {
    final response = await _api.get<Map<String, dynamic>>(
      '/tenants/$tenantId/cdrs/$cdrId',
    );

    return Cdr.fromJson(response.data!);
  }
}
