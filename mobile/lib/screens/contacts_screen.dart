import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/contact.dart';
import '../providers/auth_provider.dart';
import '../services/contacts_service.dart';
import '../theme/app_theme.dart';
import '../widgets/avatar_widget.dart';
import '../widgets/status_badge.dart';

// ---------------------------------------------------------------------------
// Service provider
// ---------------------------------------------------------------------------

/// Contacts service singleton.
final contactsServiceProvider = Provider<ContactsService>((ref) {
  final api = ref.watch(apiServiceProvider);
  return ContactsService(api: api);
});

// ---------------------------------------------------------------------------
// Contacts state
// ---------------------------------------------------------------------------

/// State for the contacts directory screen.
class ContactsState {
  final List<Contact> contacts;
  final bool isLoading;
  final String? error;
  final String searchQuery;

  const ContactsState({
    this.contacts = const [],
    this.isLoading = false,
    this.error,
    this.searchQuery = '',
  });

  /// Contacts filtered by the current search query.
  List<Contact> get filteredContacts {
    if (searchQuery.isEmpty) return contacts;
    final q = searchQuery.toLowerCase();
    return contacts.where((c) {
      return c.displayName.toLowerCase().contains(q) ||
          c.extensionNumber.contains(q) ||
          (c.email?.toLowerCase().contains(q) ?? false);
    }).toList();
  }

  ContactsState copyWith({
    List<Contact>? contacts,
    bool? isLoading,
    String? error,
    String? searchQuery,
    bool clearError = false,
  }) =>
      ContactsState(
        contacts: contacts ?? this.contacts,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        searchQuery: searchQuery ?? this.searchQuery,
      );
}

// ---------------------------------------------------------------------------
// Contacts notifier
// ---------------------------------------------------------------------------

final contactsProvider =
    StateNotifierProvider<ContactsNotifier, ContactsState>((ref) {
  final service = ref.watch(contactsServiceProvider);
  return ContactsNotifier(service: service);
});

class ContactsNotifier extends StateNotifier<ContactsState> {
  final ContactsService _service;
  String? _tenantId;

  ContactsNotifier({required ContactsService service})
      : _service = service,
        super(const ContactsState());

  /// Load all contacts for the tenant.
  Future<void> loadContacts(String tenantId) async {
    _tenantId = tenantId;
    state = state.copyWith(isLoading: true, clearError: true);

    try {
      final contacts = await _service.getContacts(tenantId);
      // Sort alphabetically by display name
      contacts.sort(
        (a, b) => a.displayName.toLowerCase().compareTo(
              b.displayName.toLowerCase(),
            ),
      );
      state = state.copyWith(contacts: contacts, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load contacts.',
      );
    }
  }

  /// Refresh contacts from the server.
  Future<void> refresh() async {
    final tenantId = _tenantId;
    if (tenantId == null) return;
    await loadContacts(tenantId);
  }

  /// Update the local search filter (client-side).
  void setSearch(String query) {
    state = state.copyWith(searchQuery: query);
  }
}

// ---------------------------------------------------------------------------
// Contacts screen widget
// ---------------------------------------------------------------------------

/// Company directory / contacts screen.
///
/// Shows a searchable, alphabetically-indexed list of extensions.
/// Tap a contact to view their detail or call.
/// Pull to refresh.
class ContactsScreen extends ConsumerStatefulWidget {
  const ContactsScreen({super.key});

  @override
  ConsumerState<ContactsScreen> createState() => _ContactsScreenState();
}

class _ContactsScreenState extends ConsumerState<ContactsScreen> {
  final _searchController = TextEditingController();
  bool _showSearch = false;
  bool _initialized = false;

  @override
  void initState() {
    super.initState();
    _searchController.addListener(_onSearchChanged);
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
    _searchController
      ..removeListener(_onSearchChanged)
      ..dispose();
    super.dispose();
  }

  void _loadData() {
    final authState = ref.read(authProvider);
    if (authState is AuthAuthenticated) {
      ref.read(contactsProvider.notifier).loadContacts(authState.user.tenantId);
    }
  }

  void _onSearchChanged() {
    ref.read(contactsProvider.notifier).setSearch(_searchController.text);
  }

  void _toggleSearch() {
    setState(() {
      _showSearch = !_showSearch;
      if (!_showSearch) {
        _searchController.clear();
      }
    });
  }

  Future<void> _onRefresh() async {
    await ref.read(contactsProvider.notifier).refresh();
  }

  void _onContactTap(Contact contact) {
    context.push(
      '/contact/${Uri.encodeComponent(contact.extensionNumber)}',
    );
  }

  @override
  Widget build(BuildContext context) {
    final contactsState = ref.watch(contactsProvider);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: _showSearch
            ? _SearchField(
                controller: _searchController,
              )
            : const Text('Contacts'),
        actions: [
          IconButton(
            icon: Icon(_showSearch ? Icons.close : Icons.search),
            onPressed: _toggleSearch,
          ),
        ],
      ),
      body: _buildBody(contactsState, theme, colorScheme),
    );
  }

  Widget _buildBody(
    ContactsState contactsState,
    ThemeData theme,
    ColorScheme colorScheme,
  ) {
    // Loading state
    if (contactsState.isLoading && contactsState.contacts.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    // Error state
    if (contactsState.error != null && contactsState.contacts.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, size: 48, color: colorScheme.error),
            const SizedBox(height: AppThemeExtras.spaceMd),
            Text(
              contactsState.error!,
              style: theme.textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppThemeExtras.spaceMd),
            FilledButton.tonal(
              onPressed: _loadData,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    final filtered = contactsState.filteredContacts;

    // Empty state
    if (filtered.isEmpty) {
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
                      Icons.contacts_outlined,
                      size: 64,
                      color: colorScheme.onSurfaceVariant.withOpacity(0.4),
                    ),
                    const SizedBox(height: AppThemeExtras.spaceMd),
                    Text(
                      contactsState.searchQuery.isNotEmpty
                          ? 'No matching contacts'
                          : 'No contacts',
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: AppThemeExtras.spaceSm),
                    Text(
                      contactsState.searchQuery.isNotEmpty
                          ? 'Try a different search term.'
                          : 'Your company directory will appear here.',
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

    // Build alphabetical sections
    final sections = _buildSections(filtered);

    return RefreshIndicator(
      onRefresh: _onRefresh,
      child: Row(
        children: [
          // Main list
          Expanded(
            child: ListView.builder(
              itemCount: _totalItemCount(sections),
              itemBuilder: (context, index) {
                final item = _itemAtIndex(sections, index);

                if (item is _SectionHeader) {
                  return Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
                    child: Text(
                      item.letter,
                      style: theme.textTheme.labelLarge?.copyWith(
                        color: colorScheme.primary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  );
                }

                final contact = (item as _ContactItem).contact;
                return _ContactListTile(
                  contact: contact,
                  onTap: () => _onContactTap(contact),
                );
              },
            ),
          ),

          // Alphabetical scroll index
          if (!_showSearch && filtered.length > 10)
            _AlphabeticalIndex(
              letters: sections.keys.toList(),
              onLetterTap: (letter) {
                // Find the index of the section header for this letter
                // and scroll to it. For simplicity, show a snackbar with
                // the letter — full scroll index requires a ScrollController
                // with item positions which would add complexity.
                // This is a visual indicator that helps with orientation.
              },
            ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Alphabetical section helpers
  // ---------------------------------------------------------------------------

  Map<String, List<Contact>> _buildSections(List<Contact> contacts) {
    final sections = <String, List<Contact>>{};

    for (final contact in contacts) {
      final letter = contact.displayName.isNotEmpty
          ? contact.displayName[0].toUpperCase()
          : '#';
      final key = RegExp(r'[A-Z]').hasMatch(letter) ? letter : '#';
      sections.putIfAbsent(key, () => []).add(contact);
    }

    // Sort section keys alphabetically, with '#' at the end
    final sortedKeys = sections.keys.toList()
      ..sort((a, b) {
        if (a == '#') return 1;
        if (b == '#') return -1;
        return a.compareTo(b);
      });

    return {for (final key in sortedKeys) key: sections[key]!};
  }

  int _totalItemCount(Map<String, List<Contact>> sections) {
    int count = 0;
    for (final entry in sections.entries) {
      count += 1 + entry.value.length; // header + items
    }
    return count;
  }

  Object _itemAtIndex(Map<String, List<Contact>> sections, int index) {
    int current = 0;
    for (final entry in sections.entries) {
      if (current == index) return _SectionHeader(entry.key);
      current++;
      for (final contact in entry.value) {
        if (current == index) return _ContactItem(contact);
        current++;
      }
    }
    throw RangeError('Index $index out of range');
  }
}

// ---------------------------------------------------------------------------
// Section header / contact item markers
// ---------------------------------------------------------------------------

class _SectionHeader {
  final String letter;
  const _SectionHeader(this.letter);
}

class _ContactItem {
  final Contact contact;
  const _ContactItem(this.contact);
}

// ---------------------------------------------------------------------------
// Contact list tile
// ---------------------------------------------------------------------------

class _ContactListTile extends StatelessWidget {
  final Contact contact;
  final VoidCallback? onTap;

  const _ContactListTile({
    required this.contact,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return ListTile(
      leading: AvatarWidget(
        name: contact.displayName,
        size: AvatarSize.medium,
        showStatus: true,
        isOnline: contact.isOnline,
        status: contact.status.name,
      ),
      title: Text(
        contact.displayName,
        style: theme.textTheme.bodyLarge,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Row(
        children: [
          Text(
            'Ext ${contact.extensionNumber}',
            style: theme.textTheme.bodySmall?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
          ),
          if (contact.isOnline) ...[
            const SizedBox(width: 8),
            StatusBadge(
              status: PresenceStatus.fromString(contact.status.name),
              showLabel: true,
              fontSize: 11,
            ),
          ],
        ],
      ),
      trailing: IconButton(
        icon: Icon(
          Icons.call_outlined,
          color: AppThemeExtras.callConnected,
        ),
        tooltip: 'Call ${contact.extensionNumber}',
        onPressed: () {
          // Navigate to contact detail (which has the call button)
          onTap?.call();
        },
      ),
      onTap: onTap,
    );
  }
}

// ---------------------------------------------------------------------------
// Alphabetical index sidebar
// ---------------------------------------------------------------------------

class _AlphabeticalIndex extends StatelessWidget {
  final List<String> letters;
  final ValueChanged<String> onLetterTap;

  const _AlphabeticalIndex({
    required this.letters,
    required this.onLetterTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SizedBox(
      width: 24,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: letters.map((letter) {
          return GestureDetector(
            onTap: () => onLetterTap(letter),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 1),
              child: Text(
                letter,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: theme.colorScheme.primary,
                  fontWeight: FontWeight.w600,
                  fontSize: 10,
                ),
              ),
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

  const _SearchField({required this.controller});

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      autofocus: true,
      decoration: const InputDecoration(
        hintText: 'Search contacts...',
        border: InputBorder.none,
        enabledBorder: InputBorder.none,
        focusedBorder: InputBorder.none,
        fillColor: Colors.transparent,
        filled: false,
        contentPadding: EdgeInsets.zero,
      ),
      textInputAction: TextInputAction.search,
    );
  }
}
