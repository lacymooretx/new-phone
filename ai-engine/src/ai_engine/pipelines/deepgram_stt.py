"""Deepgram streaming STT component via WebSocket."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

import structlog
import websockets

from ai_engine.pipelines.base import STTComponent

logger = structlog.get_logger()

DEEPGRAM_STT_URL = "wss://api.deepgram.com/v1/listen"


class DeepgramSTT(STTComponent):
    """Deepgram streaming speech-to-text via WebSocket."""

    def __init__(self, api_key: str, model: str = "nova-2", language: str = "en-US", **kwargs) -> None:
        self._api_key = api_key
        self._model = model
        self._language = language
        self._ws: websockets.WebSocketClientProtocol | None = None

    @property
    def name(self) -> str:
        return "deepgram"

    async def transcribe_stream(
        self, audio_iter: AsyncIterator[bytes], sample_rate: int
    ) -> AsyncIterator[str]:
        url = (
            f"{DEEPGRAM_STT_URL}"
            f"?model={self._model}"
            f"&language={self._language}"
            f"&encoding=linear16"
            f"&sample_rate={sample_rate}"
            f"&channels=1"
            f"&interim_results=true"
            f"&punctuate=true"
            f"&endpointing=300"
        )

        headers = {"Authorization": f"Token {self._api_key}"}
        self._ws = await websockets.connect(url, additional_headers=headers)

        # Start sending audio in background
        send_task = asyncio.create_task(self._send_audio(audio_iter))

        try:
            async for raw_msg in self._ws:
                try:
                    msg = json.loads(raw_msg)
                    channel = msg.get("channel", {})
                    alternatives = channel.get("alternatives", [])
                    if alternatives:
                        text = alternatives[0].get("transcript", "")
                        is_final = msg.get("is_final", False)
                        if text and is_final:
                            yield text
                except json.JSONDecodeError:
                    continue
        finally:
            send_task.cancel()

    async def _send_audio(self, audio_iter: AsyncIterator[bytes]) -> None:
        try:
            async for chunk in audio_iter:
                if self._ws:
                    await self._ws.send(chunk)
            if self._ws:
                await self._ws.send(json.dumps({"type": "CloseStream"}))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("deepgram_stt_send_error", error=str(e))

    async def close(self) -> None:
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
