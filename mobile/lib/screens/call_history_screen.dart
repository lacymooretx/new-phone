import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/cdr.dart';
import '../providers/auth_provider.dart';
import '../providers/cdr_provider.dart';
import '../providers/call_provider.dart';
import '../widgets/call_history_item.dart';

/// Call history screen — replaces the placeholder CallsTab.
///
/// Lists call records grouped by date (Today, Yesterday, This Week, Older).
/// Provides search, filter chips (All, Missed, Inbound, Outbound), pull to
/// refresh, and infinite scroll pagination.
class CallHistoryScreen extends ConsumerStatefulWidget {
  const CallHistoryScreen({super.key});

  @override
  ConsumerState<CallHistoryScreen> createState() => _CallHistoryScreenState();
}

class _CallHistoryScreenState extends ConsumerState<CallHistoryScreen> {
  final _scrollController = ScrollController();
  final _searchController = TextEditingController();
  bool _showSearch = false;
  bool _initialized = false;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_initialized) {
      _initialized = true;
      _loadData();
    }
  }

  @override
  void dispose() {
    _scrollController
      ..removeListener(_onScroll)
      ..dispose();
    _searchController.dispose();
    super.dispose();
  }

  void _loadData() {
    final authState = ref.read(authProvider);
    if (authState is AuthAuthenticated) {
      ref.read(cdrProvider.notifier).loadCdrs(authState.user.tenantId);
    }
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      ref.read(cdrProvider.notifier).loadMore();
    }
  }

  Future<void> _onRefresh() async {
    await ref.read(cdrProvider.notifier).refresh();
  }

  void _onSearchSubmitted(String query) {
    ref.read(cdrProvider.notifier).search(query);
  }

  void _toggleSearch() {
    setState(() {
      _showSearch = !_showSearch;
      if (!_showSearch) {
        _searchController.clear();
        ref.read(cdrProvider.notifier).search('');
      }
    });
  }

  void _onCdrTap(Cdr cdr) {
    // Navigate to contact detail with the remote party info
    context.push(
      '/contact/${Uri.encodeComponent(cdr.remotePartyNumber)}',
      extra: cdr,
    );
  }

  void _onCallBack(Cdr cdr) {
    ref.read(callProvider.notifier).makeCall(cdr.remotePartyNumber);
  }

  @override
  Widget build(BuildContext context) {
    final cdrState = ref.watch(cdrProvider);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: _showSearch
            ? _SearchField(
                controller: _searchController,
                onSubmitted: _onSearchSubmitted,
              )
            : const Text('Calls'),
        actions: [
          IconButton(
            icon: Icon(_showSearch ? Icons.close : Icons.search),
            onPressed: _toggleSearch,
          ),
        ],
      ),
      body: Column(
        children: [
          // Filter chips
          _FilterChips(
            currentFilter: cdrState.filter,
            onFilterChanged: (filter) {
              ref.read(cdrProvider.notifier).setFilter(filter);
            },
          ),

          // Content
          Expanded(
            child: _buildBody(cdrState, theme, colorScheme),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(CdrState cdrState, ThemeData theme, ColorScheme colorScheme) {
    // Loading state
    if (cdrState.isLoading && cdrState.records.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    // Error state
    if (cdrState.error != null && cdrState.records.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, size: 48, color: colorScheme.error),
            const SizedBox(height: 16),
            Text(
              cdrState.error!,
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
    if (cdrState.records.isEmpty) {
      return RefreshIndicator(
        onRefresh: _onRefresh,
        child: ListView(
          children: [
            SizedBox(
              height: MediaQuery.of(context).size.height * 0.5,
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.call_outlined,
                      size: 64,
                      color: colorScheme.onSurfaceVariant.withOpacity(0.4),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      cdrState.searchQuery.isNotEmpty
                          ? 'No matching calls'
                          : 'No recent calls',
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      cdrState.searchQuery.isNotEmpty
                          ? 'Try a different search term.'
                          : 'Your call history will appear here.',
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

    // CDR list grouped by date
    final grouped = _groupByDate(cdrState.records);

    return RefreshIndicator(
      onRefresh: _onRefresh,
      child: ListView.builder(
        controller: _scrollController,
        itemCount: _totalItemCount(grouped) + (cdrState.isLoadingMore ? 1 : 0),
        itemBuilder: (context, index) {
          final totalGrouped = _totalItemCount(grouped);

          // Loading more indicator
          if (index == totalGrouped) {
            return const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            );
          }

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

          // CDR item
          final cdr = (item as _CdrItem).cdr;
          return CallHistoryItem(
            cdr: cdr,
            onTap: () => _onCdrTap(cdr),
          );
        },
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Date grouping helpers
  // ---------------------------------------------------------------------------

  Map<String, List<Cdr>> _groupByDate(List<Cdr> records) {
    final grouped = <String, List<Cdr>>{};

    for (final cdr in records) {
      final label = _dateLabel(cdr.startTime);
      grouped.putIfAbsent(label, () => []).add(cdr);
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

    return 'Older';
  }

  int _totalItemCount(Map<String, List<Cdr>> grouped) {
    int count = 0;
    for (final entry in grouped.entries) {
      count += 1 + entry.value.length;
    }
    return count;
  }

  Object _itemAtIndex(Map<String, List<Cdr>> grouped, int index) {
    int current = 0;
    for (final entry in grouped.entries) {
      if (current == index) return _DateHeader(entry.key);
      current++;
      for (final cdr in entry.value) {
        if (current == index) return _CdrItem(cdr);
        current++;
      }
    }
    throw RangeError('Index $index out of range');
  }
}

// ---------------------------------------------------------------------------
// Date header / CDR item markers
// ---------------------------------------------------------------------------

class _DateHeader {
  final String label;
  const _DateHeader(this.label);
}

class _CdrItem {
  final Cdr cdr;
  const _CdrItem(this.cdr);
}

// ---------------------------------------------------------------------------
// Filter chips
// ---------------------------------------------------------------------------

class _FilterChips extends StatelessWidget {
  final CdrFilter currentFilter;
  final ValueChanged<CdrFilter> onFilterChanged;

  const _FilterChips({
    required this.currentFilter,
    required this.onFilterChanged,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 48,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        children: CdrFilter.values.map((filter) {
          final isSelected = filter == currentFilter;
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilterChip(
              label: Text(filter.label),
              selected: isSelected,
              onSelected: (_) => onFilterChanged(filter),
              showCheckmark: false,
            ),
          );
        }).toList(),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Search field
// ---------------------------------------------------------------------------

class _SearchField extends StatelessWidget {
  final TextEditingController controller;
  final ValueChanged<String> onSubmitted;

  const _SearchField({
    required this.controller,
    required this.onSubmitted,
  });

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      autofocus: true,
      decoration: const InputDecoration(
        hintText: 'Search calls...',
        border: InputBorder.none,
        enabledBorder: InputBorder.none,
        focusedBorder: InputBorder.none,
        fillColor: Colors.transparent,
        filled: false,
        contentPadding: EdgeInsets.zero,
      ),
      textInputAction: TextInputAction.search,
      onSubmitted: onSubmitted,
    );
  }
}
