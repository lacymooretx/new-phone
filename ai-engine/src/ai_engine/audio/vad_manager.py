"""Voice Activity Detection using WebRTC VAD + energy threshold."""

from __future__ import annotations

import webrtcvad

from ai_engine.audio.resampler import compute_rms


class VADManager:
    """Detects speech onset and offset using WebRTC VAD with energy gating."""

    def __init__(
        self,
        sample_rate: int = 8000,
        frame_duration_ms: int = 20,
        aggressiveness: int = 2,
        energy_threshold: float = 200.0,
        speech_frames_threshold: int = 3,
        silence_frames_threshold: int = 15,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.energy_threshold = energy_threshold
        self.speech_frames_threshold = speech_frames_threshold
        self.silence_frames_threshold = silence_frames_threshold

        self._vad = webrtcvad.Vad(aggressiveness)
        self._speech_frame_count = 0
        self._silence_frame_count = 0
        self._is_speaking = False

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def process_frame(self, pcm16_frame: bytes) -> bool | None:
        """Process a single audio frame.

        Returns:
            True if speech onset detected (was silent, now speaking)
            False if speech offset detected (was speaking, now silent)
            None if no state change
        """
        frame_size = 2 * self.sample_rate * self.frame_duration_ms // 1000
        if len(pcm16_frame) != frame_size:
            return None

        rms = compute_rms(pcm16_frame)
        if rms < self.energy_threshold:
            is_speech = False
        else:
            try:
                is_speech = self._vad.is_speech(pcm16_frame, self.sample_rate)
            except Exception:
                is_speech = False

        if is_speech:
            self._speech_frame_count += 1
            self._silence_frame_count = 0

            if not self._is_speaking and self._speech_frame_count >= self.speech_frames_threshold:
                self._is_speaking = True
                return True
        else:
            self._silence_frame_count += 1
            self._speech_frame_count = 0

            if self._is_speaking and self._silence_frame_count >= self.silence_frames_threshold:
                self._is_speaking = False
                return False

        return None

    def reset(self) -> None:
        self._speech_frame_count = 0
        self._silence_frame_count = 0
        self._is_speaking = False
