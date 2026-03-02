"""ElevenLabs Conversational AI provider.

Audio: 8kHz ulaw → 16kHz PCM16, output 16kHz PCM16 → 8kHz ulaw.
Client-side tool execution, native VAD/barge-in.
"""

from __future__ import annotations

import asyncio
import base64
import json

import structlog
import websockets

from ai_engine.audio.resampler import (
    ResampleState,
    pcm16_16k_to_ulaw_8k,
    ulaw_8k_to_pcm16_16k,
)
from ai_engine.providers.base import (
    AIProviderInterface,
    ProviderCapabilities,
    ProviderSessionConfig,
)
from ai_engine.services.metrics import ai_agent_provider_errors_total

logger = structlog.get_logger()

ELEVENLABS_CONVAI_URL = "wss://api.elevenlabs.io/v1/convai/conversation"


class ElevenLabsProvider(AIProviderInterface):
    """ElevenLabs Conversational AI provider."""

    def __init__(self) -> None:
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._config: ProviderSessionConfig | None = None
        self._receive_task: asyncio.Task | None = None
        self._input_resample_state = ResampleState()
        self._output_resample_state = ResampleState()

    @property
    def name(self) -> str:
        return "elevenlabs"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            input_encodings=["pcm16"],
            input_sample_rates_hz=[16000],
            output_encodings=["pcm16"],
            output_sample_rates_hz=[16000],
            is_full_agent=True,
            has_native_vad=True,
            has_native_barge_in=True,
        )

    async def start_session(self, config: ProviderSessionConfig) -> None:
        self._config = config
        url = config.base_url or ELEVENLABS_CONVAI_URL

        headers = {"xi-api-key": config.api_key}

        self._ws = await websockets.connect(url, additional_headers=headers, max_size=10_000_000)

        # Send initialization
        init_msg = {
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {
                    "prompt": {"prompt": config.system_prompt},
                    "first_message": config.greeting or "Hello, how can I help you?",
                    "language": config.language or "en",
                },
                "tts": {
                    "voice_id": config.voice_id,
                },
            },
        }

        if config.tools:
            init_msg["conversation_config_override"]["agent"]["tools"] = config.tools

        await self._ws.send(json.dumps(init_msg))

        self._receive_task = asyncio.create_task(self._receive_loop())

        logger.info("elevenlabs_session_started", call_id=config.call_id)

    async def send_audio(self, audio_chunk: bytes) -> None:
        if not self._ws:
            return

        pcm16k, self._input_resample_state = ulaw_8k_to_pcm16_16k(audio_chunk, self._input_resample_state)
        b64_audio = base64.b64encode(pcm16k).decode()

        await self._ws.send(json.dumps({
            "user_audio_chunk": b64_audio,
        }))

    async def stop_session(self) -> None:
        if self._receive_task:
            self._receive_task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        logger.info("elevenlabs_session_stopped", call_id=self._config.call_id if self._config else "")

    async def interrupt(self) -> None:
        if self._ws:
            await self._ws.send(json.dumps({"type": "user_interruption"}))

    async def _receive_loop(self) -> None:
        try:
            async for raw_msg in self._ws:
                try:
                    msg = json.loads(raw_msg)
                    await self._handle_event(msg)
                except json.JSONDecodeError:
                    continue
        except websockets.exceptions.ConnectionClosed:
            logger.info("elevenlabs_ws_closed")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            ai_agent_provider_errors_total.labels(provider="elevenlabs").inc()
            if self.on_error:
                await self.on_error(e)

    async def _handle_event(self, msg: dict) -> None:
        msg_type = msg.get("type", "")

        if msg_type == "audio":
            b64_audio = msg.get("audio_event", {}).get("audio_base_64", "")
            if b64_audio:
                pcm16k = base64.b64decode(b64_audio)
                ulaw8k, self._output_resample_state = pcm16_16k_to_ulaw_8k(
                    pcm16k, self._output_resample_state
                )
                if self.on_audio_output:
                    await self.on_audio_output(ulaw8k)

        elif msg_type == "agent_response":
            text = msg.get("agent_response_event", {}).get("agent_response", "")
            if text and self.on_transcript:
                await self.on_transcript("agent", text)

        elif msg_type == "user_transcript":
            text = msg.get("user_transcription_event", {}).get("user_transcript", "")
            if text and self.on_transcript:
                await self.on_transcript("caller", text)

        elif msg_type == "client_tool_call":
            tool_name = msg.get("client_tool_call", {}).get("tool_name", "")
            params = msg.get("client_tool_call", {}).get("parameters", {})
            if tool_name and self.on_tool_call:
                await self.on_tool_call(tool_name, params)

        elif msg_type == "agent_response_correction":
            pass  # ElevenLabs can correct previous responses

        elif msg_type == "interruption":
            pass  # Barge-in handled natively

        elif msg_type == "ping":
            await self._ws.send(json.dumps({"type": "pong", "event_id": msg.get("ping_event", {}).get("event_id")}))
