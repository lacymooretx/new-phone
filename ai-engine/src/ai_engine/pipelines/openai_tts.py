"""OpenAI TTS component via REST API."""

from __future__ import annotations

from typing import AsyncIterator

import httpx
import structlog

from ai_engine.pipelines.base import TTSComponent

logger = structlog.get_logger()


class OpenAITTS(TTSComponent):
    """OpenAI Text-to-Speech via REST API."""

    def __init__(self, api_key: str, model: str = "tts-1", voice: str = "alloy", **kwargs) -> None:
        self._api_key = api_key
        self._model = model
        self._voice = voice

    @property
    def name(self) -> str:
        return "openai"

    async def synthesize(
        self, text: str, voice_id: str | None = None
    ) -> AsyncIterator[bytes]:
        voice = voice_id or self._voice

        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "input": text,
                    "voice": voice,
                    "response_format": "pcm",
                },
            ) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes(chunk_size=4096):
                    yield chunk
