import 'dart:async';

import 'package:flutter/material.dart';

/// Audio player widget for voicemail playback.
///
/// Provides play/pause, seek bar, position/duration display, and playback
/// speed selection. Calls [onListened] when playback starts for the first
/// time so the voicemail can be marked as listened.
///
/// The actual audio playback requires the `just_audio` or `audioplayers`
/// package. Until that dependency is wired, the widget renders a fully
/// functional UI with simulated playback state so the rest of the app
/// can be built against it.
class VoicemailPlayer extends StatefulWidget {
  /// URL of the audio file to play.
  final String audioUrl;

  /// Total duration of the voicemail in seconds.
  final int durationSeconds;

  /// Auth token to attach to the audio request.
  final String? authToken;

  /// Called when the user starts playback for the first time.
  final VoidCallback? onListened;

  const VoicemailPlayer({
    super.key,
    required this.audioUrl,
    required this.durationSeconds,
    this.authToken,
    this.onListened,
  });

  @override
  State<VoicemailPlayer> createState() => _VoicemailPlayerState();
}

class _VoicemailPlayerState extends State<VoicemailPlayer> {
  bool _isPlaying = false;
  bool _hasStartedOnce = false;
  double _position = 0; // seconds
  double _playbackSpeed = 1.0;
  Timer? _simulationTimer;

  static const List<double> _speedOptions = [0.5, 1.0, 1.5, 2.0];

  double get _totalDuration => widget.durationSeconds.toDouble();

  @override
  void dispose() {
    _simulationTimer?.cancel();
    super.dispose();
  }

  void _togglePlayPause() {
    setState(() {
      _isPlaying = !_isPlaying;
    });

    if (_isPlaying) {
      if (!_hasStartedOnce) {
        _hasStartedOnce = true;
        widget.onListened?.call();
      }
      _startSimulation();
    } else {
      _stopSimulation();
    }
  }

  void _onSeek(double value) {
    setState(() {
      _position = value;
    });

    // TODO: Seek the actual audio player to this position
  }

  void _onSeekEnd(double value) {
    setState(() {
      _position = value;
    });

    // If we were playing, resume simulation
    if (_isPlaying) {
      _startSimulation();
    }
  }

  void _setPlaybackSpeed(double speed) {
    setState(() {
      _playbackSpeed = speed;
    });

    // Restart simulation with new speed if playing
    if (_isPlaying) {
      _startSimulation();
    }

    // TODO: Set actual audio player speed
  }

  void _startSimulation() {
    _stopSimulation();

    // Simulate playback progress at the selected speed
    final intervalMs = (100 / _playbackSpeed).round();
    _simulationTimer = Timer.periodic(
      Duration(milliseconds: intervalMs),
      (_) {
        if (!mounted) return;

        setState(() {
          _position += 0.1;
          if (_position >= _totalDuration) {
            _position = 0;
            _isPlaying = false;
            _stopSimulation();
          }
        });
      },
    );
  }

  void _stopSimulation() {
    _simulationTimer?.cancel();
    _simulationTimer = null;
  }

  String _formatTime(double seconds) {
    final totalSeconds = seconds.round();
    final minutes = totalSeconds ~/ 60;
    final secs = totalSeconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Play button and seek bar
        Row(
          children: [
            // Play / pause button
            IconButton(
              onPressed: _togglePlayPause,
              icon: Icon(
                _isPlaying ? Icons.pause_circle_filled : Icons.play_circle_filled,
                size: 40,
                color: colorScheme.primary,
              ),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
            ),

            // Seek bar
            Expanded(
              child: SliderTheme(
                data: SliderThemeData(
                  trackHeight: 3,
                  thumbShape: const RoundSliderThumbShape(
                    enabledThumbRadius: 6,
                  ),
                  overlayShape: const RoundSliderOverlayShape(
                    overlayRadius: 14,
                  ),
                  activeTrackColor: colorScheme.primary,
                  inactiveTrackColor: colorScheme.primary.withOpacity(0.2),
                  thumbColor: colorScheme.primary,
                ),
                child: Slider(
                  value: _position.clamp(0, _totalDuration),
                  min: 0,
                  max: _totalDuration > 0 ? _totalDuration : 1,
                  onChanged: _onSeek,
                  onChangeEnd: _onSeekEnd,
                ),
              ),
            ),
          ],
        ),

        // Time labels and speed selector
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Current position / total duration
              Text(
                '${_formatTime(_position)} / ${_formatTime(_totalDuration)}',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),

              // Playback speed selector
              _SpeedSelector(
                currentSpeed: _playbackSpeed,
                speeds: _speedOptions,
                onSpeedSelected: _setPlaybackSpeed,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Playback speed selector
// ---------------------------------------------------------------------------

class _SpeedSelector extends StatelessWidget {
  final double currentSpeed;
  final List<double> speeds;
  final ValueChanged<double> onSpeedSelected;

  const _SpeedSelector({
    required this.currentSpeed,
    required this.speeds,
    required this.onSpeedSelected,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return PopupMenuButton<double>(
      onSelected: onSpeedSelected,
      itemBuilder: (context) => speeds
          .map(
            (speed) => PopupMenuItem<double>(
              value: speed,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (speed == currentSpeed)
                    Icon(
                      Icons.check,
                      size: 16,
                      color: colorScheme.primary,
                    )
                  else
                    const SizedBox(width: 16),
                  const SizedBox(width: 8),
                  Text('${speed}x'),
                ],
              ),
            ),
          )
          .toList(),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          border: Border.all(
            color: colorScheme.outline.withOpacity(0.3),
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(
          '${currentSpeed}x',
          style: theme.textTheme.bodySmall?.copyWith(
            color: colorScheme.primary,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}
