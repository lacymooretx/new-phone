"""ElevenLabs TTS component via WebSocket streaming."""

from __future__ import annotations

import asyncio
import base64
import json
from typing import AsyncIterator

import structlog
import websockets

from ai_engine.pipelines.base import TTSComponent

logger = structlog.get_logger()

ELEVENLABS_TTS_WS_URL = "wss://api.elevenlabs.io/v1/text-to-speech"


class ElevenLabsTTS(TTSComponent):
    """ElevenLabs streaming Text-to-Speech via WebSocket."""

    def __init__(
        self,
        api_key: str,
        model_id: str = "eleven_turbo_v2_5",
        voice: str = "21m00Tcm4TlvDq8ikWAM",
        **kwargs,
    ) -> None:
        self._api_key = api_key
        self._model_id = model_id
        self._default_voice = voice

    @property
    def name(self) -> str:
        return "elevenlabs"

    async def synthesize(
        self, text: str, voice_id: str | None = None
    ) -> AsyncIterator[bytes]:
        voice = voice_id or self._default_voice
        url = (
            f"{ELEVENLABS_TTS_WS_URL}/{voice}/stream-input"
            f"?model_id={self._model_id}"
            f"&output_format=pcm_16000"
        )

        headers = {"xi-api-key": self._api_key}

        async with websockets.connect(url, additional_headers=headers) as ws:
            # Send BOS (beginning of stream)
            await ws.send(json.dumps({
                "text": " ",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                },
                "xi_api_key": self._api_key,
            }))

            # Send text
            await ws.send(json.dumps({"text": text}))

            # Send EOS (end of stream)
            await ws.send(json.dumps({"text": ""}))

            # Receive audio chunks
            async for raw_msg in ws:
                try:
                    msg = json.loads(raw_msg)
                    audio_b64 = msg.get("audio")
                    if audio_b64:
                        yield base64.b64decode(audio_b64)
                    if msg.get("isFinal"):
                        break
                except json.JSONDecodeError:
                    continue
