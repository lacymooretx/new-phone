import 'dart:async';

import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';

/// Audio player widget for voicemail playback.
///
/// Provides play/pause, seek bar, position/duration display, and playback
/// speed selection. Calls [onListened] when playback starts for the first
/// time so the voicemail can be marked as listened.
///
/// Uses the `just_audio` package for real audio playback with auth headers.
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
  AudioPlayer? _player;
  bool _hasStartedOnce = false;
  bool _isPlaying = false;
  double _position = 0; // seconds
  double _duration = 0; // seconds
  double _playbackSpeed = 1.0;

  StreamSubscription<Duration>? _positionSub;
  StreamSubscription<PlayerState>? _playerStateSub;
  StreamSubscription<Duration?>? _durationSub;

  static const List<double> _speedOptions = [0.5, 1.0, 1.5, 2.0];

  double get _totalDuration =>
      _duration > 0 ? _duration : widget.durationSeconds.toDouble();

  @override
  void dispose() {
    _positionSub?.cancel();
    _playerStateSub?.cancel();
    _durationSub?.cancel();
    _player?.dispose();
    super.dispose();
  }

  /// Lazily initialise the player on first use.
  Future<AudioPlayer> _ensurePlayer() async {
    if (_player != null) return _player!;

    final player = AudioPlayer();

    // Build auth headers if a token is available.
    final headers = <String, String>{};
    if (widget.authToken != null) {
      headers['Authorization'] = 'Bearer ${widget.authToken}';
    }

    await player.setUrl(widget.audioUrl, headers: headers);

    // Listen to position updates.
    _positionSub = player.positionStream.listen((pos) {
      if (!mounted) return;
      setState(() {
        _position = pos.inMilliseconds / 1000.0;
      });
    });

    // Listen to duration updates from the player (may differ from the
    // server-provided value once the file is loaded).
    _durationSub = player.durationStream.listen((dur) {
      if (!mounted || dur == null) return;
      setState(() {
        _duration = dur.inMilliseconds / 1000.0;
      });
    });

    // Listen to player state for play/pause/completed transitions.
    _playerStateSub = player.playerStateStream.listen((playerState) {
      if (!mounted) return;
      setState(() {
        _isPlaying = playerState.playing;
      });

      // Reset position when playback completes.
      if (playerState.processingState == ProcessingState.completed) {
        player.seek(Duration.zero);
        player.pause();
        setState(() {
          _position = 0;
          _isPlaying = false;
        });
      }
    });

    _player = player;
    return player;
  }

  Future<void> _togglePlayPause() async {
    final player = await _ensurePlayer();

    if (!_hasStartedOnce) {
      _hasStartedOnce = true;
      widget.onListened?.call();
    }

    if (player.playing) {
      await player.pause();
    } else {
      await player.play();
    }
  }

  Future<void> _onSeek(double value) async {
    setState(() {
      _position = value;
    });

    // Seek immediately so the slider feels responsive during drags.
    await _player?.seek(Duration(milliseconds: (value * 1000).round()));
  }

  Future<void> _onSeekEnd(double value) async {
    await _player?.seek(Duration(milliseconds: (value * 1000).round()));
  }

  Future<void> _setPlaybackSpeed(double speed) async {
    setState(() {
      _playbackSpeed = speed;
    });

    await _player?.setSpeed(speed);
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
