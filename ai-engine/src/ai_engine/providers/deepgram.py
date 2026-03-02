"""Deepgram Voice Agent provider — full-duplex conversational AI.

Audio: 8kHz ulaw passthrough (Deepgram supports natively — no resample needed).
"""

from __future__ import annotations

import asyncio
import json

import structlog
import websockets

from ai_engine.providers.base import (
    AIProviderInterface,
    ProviderCapabilities,
    ProviderSessionConfig,
)
from ai_engine.services.metrics import ai_agent_provider_errors_total

logger = structlog.get_logger()

DEEPGRAM_AGENT_URL = "wss://agent.deepgram.com/agent"


class DeepgramProvider(AIProviderInterface):
    """Deepgram Voice Agent provider."""

    def __init__(self) -> None:
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._config: ProviderSessionConfig | None = None
        self._receive_task: asyncio.Task | None = None

    @property
    def name(self) -> str:
        return "deepgram"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            input_encodings=["mulaw"],
            input_sample_rates_hz=[8000],
            output_encodings=["mulaw"],
            output_sample_rates_hz=[8000],
            is_full_agent=True,
            has_native_vad=True,
            has_native_barge_in=True,
        )

    async def start_session(self, config: ProviderSessionConfig) -> None:
        self._config = config
        url = config.base_url or DEEPGRAM_AGENT_URL

        headers = {"Authorization": f"Token {config.api_key}"}

        self._ws = await websockets.connect(url, additional_headers=headers, max_size=10_000_000)

        # Send settings message
        settings_msg = {
            "type": "SettingsConfiguration",
            "audio": {
                "input": {"encoding": "mulaw", "sample_rate": 8000},
                "output": {"encoding": "mulaw", "sample_rate": 8000, "container": "none"},
            },
            "agent": {
                "listen": {"model": "nova-2"},
                "think": {
                    "provider": {"type": "open_ai"},
                    "model": config.model_id or "gpt-4o-mini",
                    "instructions": config.system_prompt,
                },
                "speak": {
                    "model": "aura-asteria-en",
                },
            },
        }

        if config.voice_id:
            settings_msg["agent"]["speak"]["model"] = config.voice_id

        if config.tools:
            settings_msg["agent"]["think"]["functions"] = config.tools

        await self._ws.send(json.dumps(settings_msg))

        self._receive_task = asyncio.create_task(self._receive_loop())

        logger.info("deepgram_session_started", call_id=config.call_id)

    async def send_audio(self, audio_chunk: bytes) -> None:
        if self._ws:
            await self._ws.send(audio_chunk)

    async def stop_session(self) -> None:
        if self._receive_task:
            self._receive_task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        logger.info("deepgram_session_stopped", call_id=self._config.call_id if self._config else "")

    async def interrupt(self) -> None:
        if self._ws:
            await self._ws.send(json.dumps({"type": "Clear"}))

    async def _receive_loop(self) -> None:
        try:
            async for raw_msg in self._ws:
                if isinstance(raw_msg, bytes):
                    if self.on_audio_output:
                        await self.on_audio_output(raw_msg)
                    continue

                try:
                    msg = json.loads(raw_msg)
                    await self._handle_event(msg)
                except json.JSONDecodeError:
                    continue
        except websockets.exceptions.ConnectionClosed:
            logger.info("deepgram_ws_closed")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            ai_agent_provider_errors_total.labels(provider="deepgram").inc()
            if self.on_error:
                await self.on_error(e)

    async def _handle_event(self, msg: dict) -> None:
        msg_type = msg.get("type", "")

        if msg_type == "ConversationText":
            role = msg.get("role", "")
            content = msg.get("content", "")
            if content and self.on_transcript:
                speaker = "caller" if role == "user" else "agent"
                await self.on_transcript(speaker, content)

        elif msg_type == "FunctionCallRequest":
            fn_name = msg.get("function_name", "")
            try:
                fn_input = json.loads(msg.get("input", "{}"))
            except (json.JSONDecodeError, TypeError):
                fn_input = {}
            if fn_name and self.on_tool_call:
                await self.on_tool_call(fn_name, fn_input)

        elif msg_type == "AgentAudioDone":
            if self.on_turn_end:
                await self.on_turn_end()

        elif msg_type == "Error":
            error_msg = msg.get("message", "Unknown Deepgram error")
            logger.error("deepgram_error", error=error_msg)
            ai_agent_provider_errors_total.labels(provider="deepgram").inc()
