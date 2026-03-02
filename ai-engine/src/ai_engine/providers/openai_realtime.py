"""OpenAI Realtime API provider — full-duplex voice agent.

Audio: 8kHz ulaw → resample to 24kHz PCM16 → base64 JSON → provider
Output: 24kHz PCM16 → resample to 8kHz ulaw → FreeSWITCH
"""

from __future__ import annotations

import asyncio
import base64
import json
from time import time

import structlog
import websockets

from ai_engine.audio.resampler import (
    ResampleState,
    pcm16_24k_to_ulaw_8k,
    ulaw_8k_to_pcm16_24k,
)
from ai_engine.providers.base import (
    AIProviderInterface,
    ProviderCapabilities,
    ProviderSessionConfig,
)
from ai_engine.services.metrics import (
    ai_agent_barge_in_total,
    ai_agent_llm_latency_seconds,
    ai_agent_provider_errors_total,
)

logger = structlog.get_logger()

DEFAULT_MODEL = "gpt-4o-realtime-preview"
KEEPALIVE_INTERVAL = 15.0
MIN_COMMIT_INTERVAL = 0.1


class OpenAIRealtimeProvider(AIProviderInterface):
    """OpenAI Realtime API voice agent provider."""

    def __init__(self) -> None:
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._config: ProviderSessionConfig | None = None
        self._receive_task: asyncio.Task | None = None
        self._keepalive_task: asyncio.Task | None = None
        self._input_resample_state = ResampleState()
        self._output_resample_state = ResampleState()
        self._last_commit_time = 0.0
        self._audio_buffer = bytearray()

    @property
    def name(self) -> str:
        return "openai_realtime"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            input_encodings=["pcm16"],
            input_sample_rates_hz=[24000],
            output_encodings=["pcm16"],
            output_sample_rates_hz=[24000],
            is_full_agent=True,
            has_native_vad=True,
            has_native_barge_in=True,
        )

    async def start_session(self, config: ProviderSessionConfig) -> None:
        self._config = config
        model = config.model_id or DEFAULT_MODEL
        url = config.base_url or f"wss://api.openai.com/v1/realtime?model={model}"

        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

        self._ws = await websockets.connect(url, additional_headers=headers, max_size=10_000_000)

        # Configure session
        session_update = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": config.system_prompt,
                "voice": config.voice_id or "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {"model": "whisper-1"},
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                },
            },
        }

        if config.tools:
            session_update["session"]["tools"] = config.tools

        await self._ws.send(json.dumps(session_update))

        # Send greeting
        if config.greeting:
            await self._ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": config.greeting}],
                },
            }))
            await self._ws.send(json.dumps({"type": "response.create"}))

        self._receive_task = asyncio.create_task(self._receive_loop())
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

        logger.info("openai_realtime_session_started", call_id=config.call_id, model=model)

    async def send_audio(self, audio_chunk: bytes) -> None:
        if not self._ws:
            return

        # Convert 8kHz ulaw to 24kHz PCM16
        pcm24k, self._input_resample_state = ulaw_8k_to_pcm16_24k(audio_chunk, self._input_resample_state)

        # Base64 encode and send
        b64_audio = base64.b64encode(pcm24k).decode()
        await self._ws.send(json.dumps({
            "type": "input_audio_buffer.append",
            "audio": b64_audio,
        }))

        # Periodic commit
        now = time()
        if now - self._last_commit_time >= MIN_COMMIT_INTERVAL:
            self._last_commit_time = now

    async def stop_session(self) -> None:
        if self._keepalive_task:
            self._keepalive_task.cancel()
        if self._receive_task:
            self._receive_task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        logger.info("openai_realtime_session_stopped", call_id=self._config.call_id if self._config else "")

    async def interrupt(self) -> None:
        if self._ws:
            await self._ws.send(json.dumps({"type": "response.cancel"}))

    async def _receive_loop(self) -> None:
        try:
            async for raw_msg in self._ws:
                try:
                    msg = json.loads(raw_msg)
                    await self._handle_event(msg)
                except json.JSONDecodeError:
                    continue
        except websockets.exceptions.ConnectionClosed:
            logger.info("openai_ws_closed", call_id=self._config.call_id if self._config else "")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            ai_agent_provider_errors_total.labels(provider="openai_realtime").inc()
            if self.on_error:
                await self.on_error(e)

    async def _handle_event(self, msg: dict) -> None:
        event_type = msg.get("type", "")

        if event_type == "response.audio.delta":
            # Provider TTS audio output
            b64_audio = msg.get("delta", "")
            if b64_audio:
                pcm24k = base64.b64decode(b64_audio)
                ulaw8k, self._output_resample_state = pcm16_24k_to_ulaw_8k(
                    pcm24k, self._output_resample_state
                )
                if self.on_audio_output:
                    await self.on_audio_output(ulaw8k)

        elif event_type == "response.audio_transcript.done":
            text = msg.get("transcript", "")
            if text and self.on_transcript:
                await self.on_transcript("agent", text)

        elif event_type == "conversation.item.input_audio_transcription.completed":
            text = msg.get("transcript", "")
            if text and self.on_transcript:
                await self.on_transcript("caller", text)

        elif event_type == "response.function_call_arguments.done":
            fn_name = msg.get("name", "")
            try:
                fn_args = json.loads(msg.get("arguments", "{}"))
            except json.JSONDecodeError:
                fn_args = {}
            if fn_name and self.on_tool_call:
                await self.on_tool_call(fn_name, fn_args)

        elif event_type == "response.done":
            if self.on_turn_end:
                await self.on_turn_end()

        elif event_type == "error":
            error_msg = msg.get("error", {}).get("message", "Unknown error")
            logger.error("openai_realtime_error", error=error_msg)
            ai_agent_provider_errors_total.labels(provider="openai_realtime").inc()

    async def _keepalive_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(KEEPALIVE_INTERVAL)
                if self._ws:
                    await self._ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
        except asyncio.CancelledError:
            pass
