import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/cdr.dart';
import '../services/cdr_service.dart';
import 'auth_provider.dart';

// ---------------------------------------------------------------------------
// Service provider
// ---------------------------------------------------------------------------

/// CDR service singleton.
final cdrServiceProvider = Provider<CdrService>((ref) {
  final api = ref.watch(apiServiceProvider);
  return CdrService(api: api);
});

// ---------------------------------------------------------------------------
// CDR state
// ---------------------------------------------------------------------------

/// Active filter for the call history screen.
enum CdrFilter {
  all,
  missed,
  inbound,
  outbound;

  String get label => switch (this) {
        CdrFilter.all => 'All',
        CdrFilter.missed => 'Missed',
        CdrFilter.inbound => 'Inbound',
        CdrFilter.outbound => 'Outbound',
      };

  /// Convert to API query parameter values.
  String? get directionParam => switch (this) {
        CdrFilter.inbound => 'inbound',
        CdrFilter.outbound => 'outbound',
        _ => null,
      };

  String? get dispositionParam => switch (this) {
        CdrFilter.missed => 'missed',
        _ => null,
      };
}

/// State for the call history screen.
class CdrState {
  final List<Cdr> records;
  final int total;
  final int currentPage;
  final int pageSize;
  final bool isLoading;
  final bool isLoadingMore;
  final CdrFilter filter;
  final String searchQuery;
  final String? error;

  const CdrState({
    this.records = const [],
    this.total = 0,
    this.currentPage = 1,
    this.pageSize = 50,
    this.isLoading = false,
    this.isLoadingMore = false,
    this.filter = CdrFilter.all,
    this.searchQuery = '',
    this.error,
  });

  bool get hasMore => currentPage * pageSize < total;

  CdrState copyWith({
    List<Cdr>? records,
    int? total,
    int? currentPage,
    int? pageSize,
    bool? isLoading,
    bool? isLoadingMore,
    CdrFilter? filter,
    String? searchQuery,
    String? error,
    bool clearError = false,
  }) =>
      CdrState(
        records: records ?? this.records,
        total: total ?? this.total,
        currentPage: currentPage ?? this.currentPage,
        pageSize: pageSize ?? this.pageSize,
        isLoading: isLoading ?? this.isLoading,
        isLoadingMore: isLoadingMore ?? this.isLoadingMore,
        filter: filter ?? this.filter,
        searchQuery: searchQuery ?? this.searchQuery,
        error: clearError ? null : (error ?? this.error),
      );
}

// ---------------------------------------------------------------------------
// CDR notifier
// ---------------------------------------------------------------------------

final cdrProvider = StateNotifierProvider<CdrNotifier, CdrState>((ref) {
  final service = ref.watch(cdrServiceProvider);
  return CdrNotifier(service: service);
});

class CdrNotifier extends StateNotifier<CdrState> {
  final CdrService _service;
  String? _tenantId;

  CdrNotifier({required CdrService service})
      : _service = service,
        super(const CdrState());

  /// Load the first page of CDRs.
  Future<void> loadCdrs(String tenantId) async {
    _tenantId = tenantId;
    state = state.copyWith(isLoading: true, clearError: true);

    try {
      final page = await _service.getCdrs(
        tenantId,
        direction: state.filter.directionParam,
        disposition: state.filter.dispositionParam,
        search: state.searchQuery.isNotEmpty ? state.searchQuery : null,
        page: 1,
        pageSize: state.pageSize,
      );

      state = state.copyWith(
        records: page.items,
        total: page.total,
        currentPage: 1,
        isLoading: false,
      );
    } catch (e) {
      debugPrint('[CdrProvider] loadCdrs failed: $e');
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load call history.',
      );
    }
  }

  /// Load the next page of CDRs (infinite scroll).
  Future<void> loadMore() async {
    final tenantId = _tenantId;
    if (tenantId == null) return;
    if (state.isLoadingMore || !state.hasMore) return;

    state = state.copyWith(isLoadingMore: true);

    try {
      final nextPage = state.currentPage + 1;
      final page = await _service.getCdrs(
        tenantId,
        direction: state.filter.directionParam,
        disposition: state.filter.dispositionParam,
        search: state.searchQuery.isNotEmpty ? state.searchQuery : null,
        page: nextPage,
        pageSize: state.pageSize,
      );

      state = state.copyWith(
        records: [...state.records, ...page.items],
        total: page.total,
        currentPage: nextPage,
        isLoadingMore: false,
      );
    } catch (e) {
      debugPrint('[CdrProvider] loadMore failed: $e');
      state = state.copyWith(isLoadingMore: false);
    }
  }

  /// Refresh — reload from page 1.
  Future<void> refresh() async {
    final tenantId = _tenantId;
    if (tenantId == null) return;
    await loadCdrs(tenantId);
  }

  /// Change the active filter and reload.
  Future<void> setFilter(CdrFilter filter) async {
    if (filter == state.filter) return;

    state = state.copyWith(filter: filter);

    final tenantId = _tenantId;
    if (tenantId != null) {
      await loadCdrs(tenantId);
    }
  }

  /// Update the search query and reload.
  Future<void> search(String query) async {
    state = state.copyWith(searchQuery: query);

    final tenantId = _tenantId;
    if (tenantId != null) {
      await loadCdrs(tenantId);
    }
  }
}
