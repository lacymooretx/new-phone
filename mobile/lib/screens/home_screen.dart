import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/voicemail_provider.dart';

/// Main home screen with bottom navigation bar and four tabs.
///
/// The tab content is provided by the ShellRoute child. The Contacts and
/// Settings tabs are now fully implemented in their own screen files
/// (contacts_screen.dart and settings_screen.dart).
class HomeScreen extends ConsumerWidget {
  /// The child widget (tab content) provided by the ShellRoute.
  final Widget child;

  const HomeScreen({super.key, required this.child});

  /// Map GoRouter location to tab index.
  int _currentIndex(BuildContext context) {
    final location = GoRouterState.of(context).uri.toString();
    if (location.startsWith('/home/voicemail')) return 1;
    if (location.startsWith('/home/contacts')) return 2;
    if (location.startsWith('/home/settings')) return 3;
    return 0; // /home or /home/calls
  }

  void _onTabTapped(BuildContext context, int index) {
    switch (index) {
      case 0:
        context.go('/home/calls');
      case 1:
        context.go('/home/voicemail');
      case 2:
        context.go('/home/contacts');
      case 3:
        context.go('/home/settings');
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentIndex = _currentIndex(context);
    final vmState = ref.watch(voicemailProvider);
    final unreadCount = vmState.totalUnreadCount;

    return Scaffold(
      body: child,
      floatingActionButton: currentIndex == 0
          ? FloatingActionButton(
              onPressed: () => context.push('/dialer'),
              tooltip: 'New Call',
              child: const Icon(Icons.call),
            )
          : null,
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: (index) => _onTabTapped(context, index),
        destinations: [
          const NavigationDestination(
            icon: Icon(Icons.call_outlined),
            selectedIcon: Icon(Icons.call),
            label: 'Calls',
          ),
          NavigationDestination(
            icon: unreadCount > 0
                ? Badge(
                    label: Text(unreadCount > 99 ? '99+' : '$unreadCount'),
                    child: const Icon(Icons.voicemail_outlined),
                  )
                : const Icon(Icons.voicemail_outlined),
            selectedIcon: unreadCount > 0
                ? Badge(
                    label: Text(unreadCount > 99 ? '99+' : '$unreadCount'),
                    child: const Icon(Icons.voicemail),
                  )
                : const Icon(Icons.voicemail),
            label: 'Voicemail',
          ),
          const NavigationDestination(
            icon: Icon(Icons.contacts_outlined),
            selectedIcon: Icon(Icons.contacts),
            label: 'Contacts',
          ),
          const NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}
