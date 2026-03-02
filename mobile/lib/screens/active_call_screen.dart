import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/call_provider.dart';
import '../services/sip_service.dart';
import '../widgets/dial_pad.dart';

/// Full-screen active call UI showing call controls, duration timer, and
/// caller info. Overlays a DTMF keypad and transfer dialog on demand.
class ActiveCallScreen extends ConsumerStatefulWidget {
  const ActiveCallScreen({super.key});

  @override
  ConsumerState<ActiveCallScreen> createState() => _ActiveCallScreenState();
}

class _ActiveCallScreenState extends ConsumerState<ActiveCallScreen> {
  bool _showDtmfPad = false;

  @override
  Widget build(BuildContext context) {
    final callState = ref.watch(callProvider);

    // Navigate away when the call ends or goes idle
    ref.listen<CallState>(callProvider, (previous, next) {
      if (next is CallIdle) {
        if (context.mounted) context.go('/home/calls');
      }
      if (next is CallEnded) {
        // Stay for a moment to show "Call Ended", then navigate
        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) {
            final current = ref.read(callProvider);
            if (current is CallEnded || current is CallIdle) {
              context.go('/home/calls');
            }
          }
        });
      }
    });

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        body: Container(
          decoration: _backgroundGradient(context),
          child: SafeArea(
            child: switch (callState) {
              CallConnecting(:final remoteParty) =>
                _ConnectingView(remoteParty: remoteParty),
              CallConnected() => _ConnectedView(
                  callState: callState,
                  showDtmfPad: _showDtmfPad,
                  onToggleDtmf: () =>
                      setState(() => _showDtmfPad = !_showDtmfPad),
                ),
              CallEnded(:final remoteParty, :final totalDuration) =>
                _EndedView(
                  remoteParty: remoteParty,
                  duration: totalDuration,
                ),
              _ => const Center(
                  child: Text(
                    'No active call',
                    style: TextStyle(color: Colors.white70, fontSize: 18),
                  ),
                ),
            },
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
          colorScheme.primary.withOpacity(0.9),
          colorScheme.primary.withOpacity(0.7),
          colorScheme.primaryContainer.withOpacity(0.5),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Connecting view (outgoing call ringing)
// ---------------------------------------------------------------------------

class _ConnectingView extends ConsumerWidget {
  final CallPartyInfo remoteParty;

  const _ConnectingView({required this.remoteParty});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      children: [
        const Spacer(flex: 2),
        _CallerAvatar(name: remoteParty.label),
        const SizedBox(height: 24),
        Text(
          remoteParty.label,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 28,
            fontWeight: FontWeight.w600,
          ),
        ),
        if (remoteParty.displayName != null) ...[
          const SizedBox(height: 4),
          Text(
            remoteParty.number,
            style: const TextStyle(color: Colors.white70, fontSize: 16),
          ),
        ],
        const SizedBox(height: 12),
        const Text(
          'Calling...',
          style: TextStyle(color: Colors.white60, fontSize: 16),
        ),
        const Spacer(flex: 3),
        // End call button only
        _EndCallButton(
          onPressed: () => ref.read(callProvider.notifier).hangup(),
        ),
        const SizedBox(height: 48),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Connected view (active call with controls)
// ---------------------------------------------------------------------------

class _ConnectedView extends ConsumerWidget {
  final CallConnected callState;
  final bool showDtmfPad;
  final VoidCallback onToggleDtmf;

  const _ConnectedView({
    required this.callState,
    required this.showDtmfPad,
    required this.onToggleDtmf,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifier = ref.read(callProvider.notifier);

    return Column(
      children: [
        const Spacer(flex: 1),

        // Caller info
        _CallerAvatar(name: callState.remoteParty.label),
        const SizedBox(height: 24),
        Text(
          callState.remoteParty.label,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 28,
            fontWeight: FontWeight.w600,
          ),
        ),
        if (callState.remoteParty.displayName != null) ...[
          const SizedBox(height: 4),
          Text(
            callState.remoteParty.number,
            style: const TextStyle(color: Colors.white70, fontSize: 16),
          ),
        ],
        const SizedBox(height: 8),

        // Duration or "On Hold"
        if (callState.isOnHold)
          const Text(
            'On Hold',
            style: TextStyle(
              color: Colors.orangeAccent,
              fontSize: 16,
              fontWeight: FontWeight.w500,
            ),
          )
        else
          Text(
            _formatDuration(callState.duration),
            style: const TextStyle(color: Colors.white70, fontSize: 16),
          ),

        const Spacer(flex: 1),

        // DTMF pad overlay
        if (showDtmfPad) ...[
          DialPad(
            onDigitPressed: (digit) => notifier.sendDtmf(digit),
            buttonSize: 64,
            spacing: 12,
          ),
          const SizedBox(height: 16),
          TextButton(
            onPressed: onToggleDtmf,
            child: const Text(
              'Hide Keypad',
              style: TextStyle(color: Colors.white70, fontSize: 14),
            ),
          ),
          const SizedBox(height: 8),
        ],

        // Call controls grid
        if (!showDtmfPad) ...[
          _CallControlsGrid(
            isMuted: callState.isMuted,
            isOnHold: callState.isOnHold,
            isSpeaker: callState.isSpeaker,
            onToggleMute: () => notifier.toggleMute(),
            onToggleHold: () => notifier.toggleHold(),
            onToggleSpeaker: () => notifier.toggleSpeaker(),
            onToggleDtmf: onToggleDtmf,
            onTransfer: () => _showTransferDialog(context, ref),
          ),
          const SizedBox(height: 32),
        ],

        // End call button
        _EndCallButton(
          onPressed: () => notifier.hangup(),
        ),
        const SizedBox(height: 48),
      ],
    );
  }

  void _showTransferDialog(BuildContext context, WidgetRef ref) {
    final controller = TextEditingController();

    showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Transfer Call'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'Transfer to',
            hintText: 'Extension or number',
            prefixIcon: Icon(Icons.phone_forwarded_outlined),
          ),
          keyboardType: TextInputType.phone,
          autofocus: true,
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[0-9*#+]')),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              final target = controller.text.trim();
              if (target.isNotEmpty) {
                ref.read(callProvider.notifier).transfer(target);
                Navigator.of(dialogContext).pop();
              }
            },
            child: const Text('Transfer'),
          ),
        ],
      ),
    );
  }

  String _formatDuration(Duration d) {
    final hours = d.inHours;
    final minutes = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = d.inSeconds.remainder(60).toString().padLeft(2, '0');

    if (hours > 0) {
      return '$hours:$minutes:$seconds';
    }
    return '$minutes:$seconds';
  }
}

// ---------------------------------------------------------------------------
// Ended view
// ---------------------------------------------------------------------------

class _EndedView extends StatelessWidget {
  final CallPartyInfo remoteParty;
  final Duration duration;

  const _EndedView({
    required this.remoteParty,
    required this.duration,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _CallerAvatar(name: remoteParty.label),
          const SizedBox(height: 24),
          Text(
            remoteParty.label,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 28,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            'Call Ended',
            style: TextStyle(color: Colors.white60, fontSize: 16),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Call controls grid (3x2)
// ---------------------------------------------------------------------------

class _CallControlsGrid extends StatelessWidget {
  final bool isMuted;
  final bool isOnHold;
  final bool isSpeaker;
  final VoidCallback onToggleMute;
  final VoidCallback onToggleHold;
  final VoidCallback onToggleSpeaker;
  final VoidCallback onToggleDtmf;
  final VoidCallback onTransfer;

  const _CallControlsGrid({
    required this.isMuted,
    required this.isOnHold,
    required this.isSpeaker,
    required this.onToggleMute,
    required this.onToggleHold,
    required this.onToggleSpeaker,
    required this.onToggleDtmf,
    required this.onTransfer,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _CallControlButton(
                icon: isMuted ? Icons.mic_off : Icons.mic,
                label: 'Mute',
                isActive: isMuted,
                onPressed: onToggleMute,
              ),
              _CallControlButton(
                icon: Icons.dialpad,
                label: 'Keypad',
                onPressed: onToggleDtmf,
              ),
              _CallControlButton(
                icon: isSpeaker ? Icons.volume_up : Icons.volume_up_outlined,
                label: 'Speaker',
                isActive: isSpeaker,
                onPressed: onToggleSpeaker,
              ),
            ],
          ),
          const SizedBox(height: 24),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _CallControlButton(
                icon: isOnHold ? Icons.play_arrow : Icons.pause,
                label: 'Hold',
                isActive: isOnHold,
                onPressed: onToggleHold,
              ),
              _CallControlButton(
                icon: Icons.phone_forwarded_outlined,
                label: 'Transfer',
                onPressed: onTransfer,
              ),
              // Placeholder for symmetry
              const SizedBox(width: 72),
            ],
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Reusable call control button
// ---------------------------------------------------------------------------

class _CallControlButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isActive;
  final VoidCallback onPressed;

  const _CallControlButton({
    required this.icon,
    required this.label,
    this.isActive = false,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 64,
          height: 64,
          child: Material(
            color: isActive
                ? Colors.white.withOpacity(0.3)
                : Colors.white.withOpacity(0.1),
            shape: const CircleBorder(),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onTap: () {
                HapticFeedback.lightImpact();
                onPressed();
              },
              customBorder: const CircleBorder(),
              child: Center(
                child: Icon(
                  icon,
                  color: isActive ? Colors.white : Colors.white70,
                  size: 28,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 6),
        Text(
          label,
          style: TextStyle(
            color: isActive ? Colors.white : Colors.white70,
            fontSize: 12,
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// End call button
// ---------------------------------------------------------------------------

class _EndCallButton extends StatelessWidget {
  final VoidCallback onPressed;

  const _EndCallButton({required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 72,
      height: 72,
      child: Material(
        color: Colors.red,
        shape: const CircleBorder(),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () {
            HapticFeedback.mediumImpact();
            onPressed();
          },
          customBorder: const CircleBorder(),
          child: const Center(
            child: Icon(
              Icons.call_end,
              color: Colors.white,
              size: 32,
            ),
          ),
        ),
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
      radius: 48,
      backgroundColor: Colors.white.withOpacity(0.2),
      child: Text(
        _initials(name),
        style: const TextStyle(
          color: Colors.white,
          fontSize: 32,
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
