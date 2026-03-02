import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'config/router.dart';
import 'config/theme.dart';
import 'providers/settings_provider.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    const ProviderScope(
      child: NewPhoneApp(),
    ),
  );
}

class NewPhoneApp extends ConsumerStatefulWidget {
  const NewPhoneApp({super.key});

  @override
  ConsumerState<NewPhoneApp> createState() => _NewPhoneAppState();
}

class _NewPhoneAppState extends ConsumerState<NewPhoneApp> {
  @override
  void initState() {
    super.initState();
    // Load persisted settings (theme mode, etc.) on startup.
    ref.read(settingsProvider.notifier).load();
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);
    final settings = ref.watch(settingsProvider);

    return MaterialApp.router(
      title: 'New Phone',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: settings.themeMode,
      routerConfig: router,
    );
  }
}
