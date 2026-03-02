"""OpenAI Whisper STT component via REST API (near-real-time)."""

from __future__ import annotations

import io
import struct
import wave
from typing import AsyncIterator

import httpx
import structlog

from ai_engine.pipelines.base import STTComponent

logger = structlog.get_logger()


class OpenAISTT(STTComponent):
    """OpenAI Whisper speech-to-text via REST API."""

    def __init__(self, api_key: str, model: str = "whisper-1", language: str = "en", **kwargs) -> None:
        self._api_key = api_key
        self._model = model
        self._language = language

    @property
    def name(self) -> str:
        return "openai_whisper"

    async def transcribe_stream(
        self, audio_iter: AsyncIterator[bytes], sample_rate: int
    ) -> AsyncIterator[str]:
        """Accumulate audio chunks and transcribe via Whisper REST API.

        Since Whisper is not a streaming API, we accumulate audio until
        silence is detected (no more chunks), then send for transcription.
        """
        buffer = bytearray()
        async for chunk in audio_iter:
            buffer.extend(chunk)

        if not buffer:
            return

        wav_data = self._pcm16_to_wav(bytes(buffer), sample_rate)
        text = await self._transcribe(wav_data)
        if text:
            yield text

    def _pcm16_to_wav(self, pcm_data: bytes, sample_rate: int) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        return buf.getvalue()

    async def _transcribe(self, wav_data: bytes) -> str:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    files={"file": ("audio.wav", wav_data, "audio/wav")},
                    data={"model": self._model, "language": self._language},
                )
                resp.raise_for_status()
                return resp.json().get("text", "")
        except Exception as e:
            logger.error("openai_stt_error", error=str(e))
            return ""
