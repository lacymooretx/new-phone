"""Audio format conversion utilities for AI voice agent providers.

Provider format matrix:
- FreeSWITCH:  8kHz ulaw (default mod_audio_fork output)
- OpenAI:      24kHz PCM16 little-endian
- Deepgram:    8kHz ulaw (native — no conversion needed)
- Google:      16kHz PCM16 input, 24kHz PCM16 output
- ElevenLabs:  16kHz PCM16 input/output
"""

from __future__ import annotations

import audioop
import struct
from dataclasses import dataclass


@dataclass
class ResampleState:
    """Holds state for continuous resampling across chunks."""

    state: tuple | None = None


def ulaw_to_pcm16(data: bytes) -> bytes:
    """Convert u-law encoded audio to 16-bit signed PCM."""
    return audioop.ulaw2lin(data, 2)


def pcm16_to_ulaw(data: bytes) -> bytes:
    """Convert 16-bit signed PCM audio to u-law encoding."""
    return audioop.lin2ulaw(data, 2)


def resample(
    data: bytes,
    src_rate: int,
    dst_rate: int,
    state: ResampleState | None = None,
) -> tuple[bytes, ResampleState]:
    """Resample PCM16 audio from src_rate to dst_rate.

    Returns (resampled_data, updated_state) for continuous streaming.
    """
    if src_rate == dst_rate:
        return data, state or ResampleState()

    rs = state or ResampleState()
    resampled, rs.state = audioop.ratecv(data, 2, 1, src_rate, dst_rate, rs.state)
    return resampled, rs


def ulaw_8k_to_pcm16_24k(data: bytes, state: ResampleState | None = None) -> tuple[bytes, ResampleState]:
    """Convert 8kHz u-law to 24kHz PCM16 (for OpenAI Realtime)."""
    pcm = ulaw_to_pcm16(data)
    return resample(pcm, 8000, 24000, state)


def pcm16_24k_to_ulaw_8k(data: bytes, state: ResampleState | None = None) -> tuple[bytes, ResampleState]:
    """Convert 24kHz PCM16 to 8kHz u-law (from OpenAI Realtime)."""
    resampled, rs = resample(data, 24000, 8000, state)
    return pcm16_to_ulaw(resampled), rs


def ulaw_8k_to_pcm16_16k(data: bytes, state: ResampleState | None = None) -> tuple[bytes, ResampleState]:
    """Convert 8kHz u-law to 16kHz PCM16 (for Google/ElevenLabs)."""
    pcm = ulaw_to_pcm16(data)
    return resample(pcm, 8000, 16000, state)


def pcm16_16k_to_ulaw_8k(data: bytes, state: ResampleState | None = None) -> tuple[bytes, ResampleState]:
    """Convert 16kHz PCM16 to 8kHz u-law (from Google/ElevenLabs)."""
    resampled, rs = resample(data, 16000, 8000, state)
    return pcm16_to_ulaw(resampled), rs


def pcm16_24k_to_pcm16_8k(data: bytes, state: ResampleState | None = None) -> tuple[bytes, ResampleState]:
    """Downsample 24kHz PCM16 to 8kHz PCM16."""
    return resample(data, 24000, 8000, state)


def compute_rms(pcm16_data: bytes) -> float:
    """Compute RMS energy of PCM16 audio for VAD energy detection."""
    if len(pcm16_data) < 2:
        return 0.0
    return audioop.rms(pcm16_data, 2)
