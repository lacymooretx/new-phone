import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

// ---------------------------------------------------------------------------
// Dial pad button data
// ---------------------------------------------------------------------------

/// Represents a single button on the dial pad.
class _DialPadKey {
  final String digit;
  final String letters;

  const _DialPadKey({required this.digit, this.letters = ''});
}

const _keys = [
  _DialPadKey(digit: '1', letters: ''),
  _DialPadKey(digit: '2', letters: 'ABC'),
  _DialPadKey(digit: '3', letters: 'DEF'),
  _DialPadKey(digit: '4', letters: 'GHI'),
  _DialPadKey(digit: '5', letters: 'JKL'),
  _DialPadKey(digit: '6', letters: 'MNO'),
  _DialPadKey(digit: '7', letters: 'PQRS'),
  _DialPadKey(digit: '8', letters: 'TUV'),
  _DialPadKey(digit: '9', letters: 'WXYZ'),
  _DialPadKey(digit: '*', letters: ''),
  _DialPadKey(digit: '0', letters: '+'),
  _DialPadKey(digit: '#', letters: ''),
];

// ---------------------------------------------------------------------------
// Dial pad widget
// ---------------------------------------------------------------------------

/// Reusable 4x3 dial pad widget.
///
/// Renders 12 buttons (1-9, *, 0, #) in a grid with optional letter labels.
/// Provides haptic feedback on each press and invokes [onDigitPressed].
class DialPad extends StatelessWidget {
  /// Called when a digit is pressed.
  final ValueChanged<String> onDigitPressed;

  /// Whether to play DTMF tones on press.
  final bool playDtmfTones;

  /// Size of each button. Defaults to 76.
  final double buttonSize;

  /// Spacing between buttons.
  final double spacing;

  const DialPad({
    super.key,
    required this.onDigitPressed,
    this.playDtmfTones = false,
    this.buttonSize = 76,
    this.spacing = 16,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (int row = 0; row < 4; row++)
          Padding(
            padding: EdgeInsets.only(bottom: row < 3 ? spacing : 0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                for (int col = 0; col < 3; col++) ...[
                  if (col > 0) SizedBox(width: spacing),
                  _DialPadButton(
                    keyData: _keys[row * 3 + col],
                    size: buttonSize,
                    onPressed: () => _handlePress(context, _keys[row * 3 + col].digit),
                  ),
                ],
              ],
            ),
          ),
      ],
    );
  }

  void _handlePress(BuildContext context, String digit) {
    // Haptic feedback
    HapticFeedback.lightImpact();

    // TODO: If playDtmfTones is true, play the corresponding DTMF tone
    // via AudioService or a tone generator.

    onDigitPressed(digit);
  }
}

// ---------------------------------------------------------------------------
// Individual dial pad button
// ---------------------------------------------------------------------------

class _DialPadButton extends StatelessWidget {
  final _DialPadKey keyData;
  final double size;
  final VoidCallback onPressed;

  const _DialPadButton({
    required this.keyData,
    required this.size,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return SizedBox(
      width: size,
      height: size,
      child: Material(
        color: colorScheme.surfaceContainerHighest.withOpacity(0.4),
        shape: const CircleBorder(),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onPressed,
          customBorder: const CircleBorder(),
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  keyData.digit,
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w400,
                    color: colorScheme.onSurface,
                  ),
                ),
                if (keyData.letters.isNotEmpty)
                  Text(
                    keyData.letters,
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w500,
                      letterSpacing: 2,
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
