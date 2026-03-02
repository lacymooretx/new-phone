import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/call_provider.dart';
import '../services/sip_service.dart';

/// Full-screen incoming call UI with accept / decline buttons and a
/// slide-to-answer gesture. Designed to work over the lock screen via
/// CallKit (iOS) / ConnectionService (Android).
class IncomingCallScreen extends ConsumerStatefulWidget {
  const IncomingCallScreen({super.key});

  @override
  ConsumerState<IncomingCallScreen> createState() =>
      _IncomingCallScreenState();
}

class _IncomingCallScreenState extends ConsumerState<IncomingCallScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  Future<void> _onAnswer() async {
    HapticFeedback.mediumImpact();
    await ref.read(callProvider.notifier).answer();
  }

  Future<void> _onDecline() async {
    HapticFeedback.mediumImpact();
    await ref.read(callProvider.notifier).hangup();
  }

  @override
  Widget build(BuildContext context) {
    final callState = ref.watch(callProvider);

    // Navigate when call state changes
    ref.listen<CallState>(callProvider, (previous, next) {
      if (next is CallConnected || next is CallConnecting) {
        context.go('/call/active');
      }
      if (next is CallIdle || next is CallEnded) {
        context.go('/home/calls');
      }
    });

    // Extract caller info
    CallPartyInfo? remoteParty;
    if (callState is CallRinging) {
      remoteParty = callState.remoteParty;
    }

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        body: Container(
          decoration: _backgroundGradient(context),
          child: SafeArea(
            child: Column(
              children: [
                const Spacer(flex: 2),

                // Pulsing avatar
                AnimatedBuilder(
                  animation: _pulseController,
                  builder: (context, child) {
                    final scale =
                        1.0 + (_pulseController.value * 0.05);
                    return Transform.scale(
                      scale: scale,
                      child: child,
                    );
                  },
                  child: _CallerAvatar(
                    name: remoteParty?.label ?? 'Unknown',
                  ),
                ),

                const SizedBox(height: 24),

                // Caller name
                Text(
                  remoteParty?.label ?? 'Unknown Caller',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 32,
                    fontWeight: FontWeight.w600,
                  ),
                ),

                // Caller number (if display name is available)
                if (remoteParty?.displayName != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    remoteParty!.number,
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 18,
                    ),
                  ),
                ],

                const SizedBox(height: 12),

                // "Incoming Call" label
                const Text(
                  'Incoming Call',
                  style: TextStyle(
                    color: Colors.white60,
                    fontSize: 16,
                  ),
                ),

                const Spacer(flex: 2),

                // Slide-to-answer widget
                _SlideToAnswer(onAnswer: _onAnswer),

                const SizedBox(height: 32),

                // Accept / Decline buttons
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 48),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      // Decline
                      _CircleActionButton(
                        icon: Icons.call_end,
                        label: 'Decline',
                        color: Colors.red,
                        onPressed: _onDecline,
                      ),
                      // Accept
                      _CircleActionButton(
                        icon: Icons.call,
                        label: 'Accept',
                        color: const Color(0xFF4CAF50),
                        onPressed: _onAnswer,
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 48),
              ],
            ),
          ),
        ),
      ),
    );
  }

  BoxDecoration _backgroundGradient(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return BoxDecoration(
      gradient: LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          colorScheme.primary.withOpacity(0.95),
          colorScheme.primary.withOpacity(0.8),
          colorScheme.primaryContainer.withOpacity(0.6),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Caller avatar
// ---------------------------------------------------------------------------

class _CallerAvatar extends StatelessWidget {
  final String name;

  const _CallerAvatar({required this.name});

  @override
  Widget build(BuildContext context) {
    return CircleAvatar(
      radius: 56,
      backgroundColor: Colors.white.withOpacity(0.2),
      child: Text(
        _initials(name),
        style: const TextStyle(
          color: Colors.white,
          fontSize: 36,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  String _initials(String text) {
    final parts = text.trim().split(RegExp(r'\s+'));
    if (parts.length >= 2) {
      return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
    }
    if (text.isNotEmpty) {
      return text[0].toUpperCase();
    }
    return '?';
  }
}

// ---------------------------------------------------------------------------
// Circle action button (accept / decline)
// ---------------------------------------------------------------------------

class _CircleActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onPressed;

  const _CircleActionButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 72,
          height: 72,
          child: Material(
            color: color,
            shape: const CircleBorder(),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onTap: onPressed,
              customBorder: const CircleBorder(),
              child: Center(
                child: Icon(icon, color: Colors.white, size: 32),
              ),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          label,
          style: const TextStyle(color: Colors.white70, fontSize: 14),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Slide-to-answer widget
// ---------------------------------------------------------------------------

class _SlideToAnswer extends StatefulWidget {
  final VoidCallback onAnswer;

  const _SlideToAnswer({required this.onAnswer});

  @override
  State<_SlideToAnswer> createState() => _SlideToAnswerState();
}

class _SlideToAnswerState extends State<_SlideToAnswer>
    with SingleTickerProviderStateMixin {
  static const double _trackHeight = 64;
  static const double _thumbSize = 56;
  static const double _trackHPadding = 4;

  double _dragPosition = 0;
  double _maxDrag = 0;
  bool _answered = false;

  late final AnimationController _shimmerController;

  @override
  void initState() {
    super.initState();
    _shimmerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat();
  }

  @override
  void dispose() {
    _shimmerController.dispose();
    super.dispose();
  }

  void _onPanStart(DragStartDetails details) {
    // Nothing to initialize
  }

  void _onPanUpdate(DragUpdateDetails details) {
    if (_answered) return;

    setState(() {
      _dragPosition = (_dragPosition + details.delta.dx)
          .clamp(0, _maxDrag);
    });
  }

  void _onPanEnd(DragEndDetails details) {
    if (_answered) return;

    // Threshold: 80% of track width
    if (_dragPosition >= _maxDrag * 0.8) {
      setState(() {
        _answered = true;
        _dragPosition = _maxDrag;
      });
      HapticFeedback.heavyImpact();
      widget.onAnswer();
    } else {
      // Snap back
      setState(() => _dragPosition = 0);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 48),
      child: LayoutBuilder(
        builder: (context, constraints) {
          _maxDrag = constraints.maxWidth -
              _thumbSize -
              (_trackHPadding * 2);

          return Container(
            height: _trackHeight,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.15),
              borderRadius: BorderRadius.circular(_trackHeight / 2),
            ),
            child: Stack(
              alignment: Alignment.centerLeft,
              children: [
                // Label
                Center(
                  child: AnimatedBuilder(
                    animation: _shimmerController,
                    builder: (context, child) {
                      return Opacity(
                        opacity: _dragPosition > 10
                            ? 0
                            : 0.5 +
                                0.3 *
                                    math.sin(
                                      _shimmerController.value * 2 * math.pi,
                                    ),
                        child: child,
                      );
                    },
                    child: const Text(
                      'Slide to answer',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                  ),
                ),

                // Thumb
                Positioned(
                  left: _trackHPadding + _dragPosition,
                  child: GestureDetector(
                    onPanStart: _onPanStart,
                    onPanUpdate: _onPanUpdate,
                    onPanEnd: _onPanEnd,
                    child: Container(
                      width: _thumbSize,
                      height: _thumbSize,
                      decoration: const BoxDecoration(
                        color: Color(0xFF4CAF50),
                        shape: BoxShape.circle,
                      ),
                      child: const Center(
                        child: Icon(
                          Icons.call,
                          color: Colors.white,
                          size: 28,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
