import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/call_provider.dart';
import '../widgets/dial_pad.dart';

/// Full-screen dial pad for originating outgoing calls.
class DialerScreen extends ConsumerStatefulWidget {
  const DialerScreen({super.key});

  @override
  ConsumerState<DialerScreen> createState() => _DialerScreenState();
}

class _DialerScreenState extends ConsumerState<DialerScreen> {
  final _numberController = TextEditingController();

  @override
  void dispose() {
    _numberController.dispose();
    super.dispose();
  }

  void _onDigitPressed(String digit) {
    _numberController.text += digit;
    // Move cursor to end
    _numberController.selection = TextSelection.fromPosition(
      TextPosition(offset: _numberController.text.length),
    );
  }

  void _onBackspace() {
    final text = _numberController.text;
    if (text.isNotEmpty) {
      HapticFeedback.lightImpact();
      _numberController.text = text.substring(0, text.length - 1);
      _numberController.selection = TextSelection.fromPosition(
        TextPosition(offset: _numberController.text.length),
      );
    }
  }

  void _onBackspaceLongPress() {
    if (_numberController.text.isNotEmpty) {
      HapticFeedback.mediumImpact();
      _numberController.text = '';
    }
  }

  Future<void> _onCall() async {
    final number = _numberController.text.trim();
    if (number.isEmpty) return;

    HapticFeedback.mediumImpact();
    await ref.read(callProvider.notifier).makeCall(number);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final bottomPadding = MediaQuery.of(context).padding.bottom;

    // Listen for call state changes to navigate to active call screen
    ref.listen<CallState>(callProvider, (previous, next) {
      if (next is CallConnecting || next is CallConnected) {
        context.go('/call/active');
      }
    });

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('Dial'),
      ),
      body: SafeArea(
        child: Column(
          children: [
            const Spacer(flex: 1),

            // Number input field
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _numberController,
                      decoration: const InputDecoration(
                        hintText: 'Enter number',
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        fillColor: Colors.transparent,
                        filled: false,
                        contentPadding: EdgeInsets.zero,
                      ),
                      style: theme.textTheme.headlineMedium?.copyWith(
                        fontWeight: FontWeight.w400,
                        letterSpacing: 1.5,
                      ),
                      textAlign: TextAlign.center,
                      keyboardType: TextInputType.phone,
                      showCursor: true,
                      // Allow paste from clipboard
                      inputFormatters: [
                        FilteringTextInputFormatter.allow(
                          RegExp(r'[0-9*#+\-() ]'),
                        ),
                      ],
                    ),
                  ),
                  // Backspace button — only visible when there is text
                  ValueListenableBuilder<TextEditingValue>(
                    valueListenable: _numberController,
                    builder: (context, value, child) {
                      if (value.text.isEmpty) {
                        return const SizedBox(width: 48, height: 48);
                      }
                      return GestureDetector(
                        onLongPress: _onBackspaceLongPress,
                        child: IconButton(
                          onPressed: _onBackspace,
                          icon: Icon(
                            Icons.backspace_outlined,
                            color: colorScheme.onSurfaceVariant,
                          ),
                          tooltip: 'Backspace',
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // Dial pad
            DialPad(onDigitPressed: _onDigitPressed),

            const SizedBox(height: 24),

            // Call button
            SizedBox(
              width: 72,
              height: 72,
              child: FloatingActionButton(
                heroTag: 'dialer_call_btn',
                onPressed: _onCall,
                backgroundColor: const Color(0xFF4CAF50),
                foregroundColor: Colors.white,
                elevation: 4,
                shape: const CircleBorder(),
                child: const Icon(Icons.call, size: 32),
              ),
            ),

            SizedBox(height: 16 + bottomPadding),
          ],
        ),
      ),
    );
  }
}
