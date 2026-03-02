"""Tests for ai_engine.audio.resampler — audio conversion with mocked audioop."""

from __future__ import annotations

import sys

from ai_engine.audio.resampler import (
    ResampleState,
    compute_rms,
    pcm16_16k_to_ulaw_8k,
    pcm16_24k_to_pcm16_8k,
    pcm16_24k_to_ulaw_8k,
    pcm16_to_ulaw,
    resample,
    ulaw_8k_to_pcm16_16k,
    ulaw_8k_to_pcm16_24k,
    ulaw_to_pcm16,
)

# Grab the mock from sys.modules so we can configure/assert on it
_mock_audioop = sys.modules["audioop"]


class TestUlawToPcm16:
    def test_calls_audioop(self):
        data = b"\x7f" * 160
        result = ulaw_to_pcm16(data)
        _mock_audioop.ulaw2lin.assert_called_with(data, 2)
        assert isinstance(result, bytes)


class TestPcm16ToUlaw:
    def test_calls_audioop(self):
        data = b"\x00\x00" * 160
        result = pcm16_to_ulaw(data)
        _mock_audioop.lin2ulaw.assert_called_with(data, 2)
        assert isinstance(result, bytes)


class TestResample:
    def test_same_rate_noop(self):
        data = b"\x00\x00" * 100
        result, state = resample(data, 8000, 8000)
        assert result == data
        assert isinstance(state, ResampleState)

    def test_different_rate_calls_ratecv(self):
        data = b"\x00\x00" * 100
        _result, _state = resample(data, 8000, 16000)
        _mock_audioop.ratecv.assert_called()

    def test_state_preserved(self):
        data = b"\x00\x00" * 100
        _, state1 = resample(data, 8000, 16000)
        # Second call with existing state
        _, state2 = resample(data, 8000, 16000, state1)
        assert isinstance(state2, ResampleState)


class TestConvenienceConverters:
    def test_ulaw_8k_to_pcm16_24k(self):
        data = b"\x7f" * 160
        result, state = ulaw_8k_to_pcm16_24k(data)
        assert isinstance(result, bytes)
        assert isinstance(state, ResampleState)

    def test_pcm16_24k_to_ulaw_8k(self):
        data = b"\x00\x00" * 480
        result, _state = pcm16_24k_to_ulaw_8k(data)
        assert isinstance(result, bytes)

    def test_ulaw_8k_to_pcm16_16k(self):
        data = b"\x7f" * 160
        result, _state = ulaw_8k_to_pcm16_16k(data)
        assert isinstance(result, bytes)

    def test_pcm16_16k_to_ulaw_8k(self):
        data = b"\x00\x00" * 320
        result, _state = pcm16_16k_to_ulaw_8k(data)
        assert isinstance(result, bytes)

    def test_pcm16_24k_to_pcm16_8k(self):
        data = b"\x00\x00" * 480
        result, _state = pcm16_24k_to_pcm16_8k(data)
        assert isinstance(result, bytes)


class TestComputeRms:
    def test_returns_float(self):
        data = b"\x00\x00" * 160
        result = compute_rms(data)
        assert isinstance(result, float)

    def test_empty_data(self):
        result = compute_rms(b"")
        assert result == 0.0

    def test_single_byte(self):
        result = compute_rms(b"\x00")
        assert result == 0.0
