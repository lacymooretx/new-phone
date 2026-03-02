"""Tests for ai_engine.audio.vad_manager — speech onset/offset detection."""

from __future__ import annotations

import sys

from ai_engine.audio.vad_manager import VADManager

# Get the mock audioop to control RMS return values
_mock_audioop = sys.modules["audioop"]


class TestVADManagerInit:
    def test_defaults(self):
        vad = VADManager()
        assert vad.sample_rate == 8000
        assert vad.frame_duration_ms == 20
        assert vad.energy_threshold == 200.0
        assert vad.speech_frames_threshold == 3
        assert vad.silence_frames_threshold == 15
        assert vad.is_speaking is False

    def test_custom_params(self):
        vad = VADManager(
            sample_rate=16000,
            frame_duration_ms=30,
            aggressiveness=3,
            energy_threshold=500.0,
            speech_frames_threshold=5,
            silence_frames_threshold=10,
        )
        assert vad.sample_rate == 16000
        assert vad.energy_threshold == 500.0


class TestProcessFrame:
    def test_wrong_size_returns_none(self):
        vad = VADManager(sample_rate=8000, frame_duration_ms=20)
        # Frame should be 320 bytes (8000 * 20 / 1000 * 2)
        result = vad.process_frame(b"\x00" * 100)  # wrong size
        assert result is None

    def test_correct_frame_size(self):
        vad = VADManager(sample_rate=8000, frame_duration_ms=20)
        frame_size = 2 * 8000 * 20 // 1000  # 320 bytes
        result = vad.process_frame(b"\x00" * frame_size)
        # With RMS=0 (below threshold), should not detect speech
        assert result is None

    def test_speech_onset(self):
        """After enough speech frames, should return True (onset)."""
        vad = VADManager(
            sample_rate=8000,
            frame_duration_ms=20,
            speech_frames_threshold=3,
            energy_threshold=100.0,
        )
        frame_size = 320  # 2 * 8000 * 20 / 1000
        frame = b"\x00\x01" * (frame_size // 2)

        # Mock RMS to be above threshold
        _mock_audioop.rms.return_value = 500.0
        # Mock Vad.is_speech to return True
        vad._vad._speech = True

        results = []
        for _ in range(5):
            r = vad.process_frame(frame)
            results.append(r)

        # Should get True on 3rd frame (onset)
        assert True in results
        assert vad.is_speaking is True

    def test_speech_offset(self):
        """After speaking, enough silence frames should return False (offset)."""
        vad = VADManager(
            sample_rate=8000,
            frame_duration_ms=20,
            speech_frames_threshold=2,
            silence_frames_threshold=3,
            energy_threshold=100.0,
        )
        frame_size = 320
        frame = b"\x00\x01" * (frame_size // 2)

        # Phase 1: Trigger speech onset
        _mock_audioop.rms.return_value = 500.0
        vad._vad._speech = True
        for _ in range(3):
            vad.process_frame(frame)
        assert vad.is_speaking is True

        # Phase 2: Send silence frames
        _mock_audioop.rms.return_value = 50.0  # below threshold
        vad._vad._speech = False

        results = []
        for _ in range(5):
            r = vad.process_frame(frame)
            results.append(r)

        assert False in results
        assert vad.is_speaking is False

    def test_low_energy_skips_vad(self):
        """When RMS is below energy_threshold, is_speech should be False."""
        vad = VADManager(energy_threshold=200.0)
        frame_size = 320
        frame = b"\x00\x00" * (frame_size // 2)

        _mock_audioop.rms.return_value = 100.0  # below 200
        vad._vad._speech = True  # VAD would say speech, but energy says no

        for _ in range(10):
            vad.process_frame(frame)

        assert vad.is_speaking is False


class TestReset:
    def test_reset_clears_state(self):
        vad = VADManager(speech_frames_threshold=2, energy_threshold=100.0)
        frame_size = 320
        frame = b"\x00\x01" * (frame_size // 2)

        # Trigger onset
        _mock_audioop.rms.return_value = 500.0
        vad._vad._speech = True
        for _ in range(3):
            vad.process_frame(frame)
        assert vad.is_speaking is True

        vad.reset()
        assert vad.is_speaking is False
