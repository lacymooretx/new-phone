"""Google Gemini Live API provider — multimodal conversational AI.

Audio: 8kHz ulaw → 16kHz PCM16 input, 24kHz PCM16 output → 8kHz ulaw.
"""

from __future__ import annotations

import asyncio
import base64
import json

import structlog
import websockets

from ai_engine.audio.resampler import (
    ResampleState,
    pcm16_24k_to_ulaw_8k,
    ulaw_8k_to_pcm16_16k,
)
from ai_engine.providers.base import (
    AIProviderInterface,
    ProviderCapabilities,
    ProviderSessionConfig,
)
from ai_engine.services.metrics import ai_agent_provider_errors_total

logger = structlog.get_logger()

GEMINI_LIVE_URL = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"


class GoogleLiveProvider(AIProviderInterface):
    """Google Gemini Live API voice agent provider."""

    def __init__(self) -> None:
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._config: ProviderSessionConfig | None = None
        self._receive_task: asyncio.Task | None = None
        self._input_resample_state = ResampleState()
        self._output_resample_state = ResampleState()

    @property
    def name(self) -> str:
        return "google_live"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            input_encodings=["pcm16"],
            input_sample_rates_hz=[16000],
            output_encodings=["pcm16"],
            output_sample_rates_hz=[24000],
            is_full_agent=True,
            has_native_vad=True,
            has_native_barge_in=True,
        )

    async def start_session(self, config: ProviderSessionConfig) -> None:
        self._config = config
        model = config.model_id or "gemini-2.0-flash-exp"
        url = config.base_url or f"{GEMINI_LIVE_URL}?key={config.api_key}"

        self._ws = await websockets.connect(url, max_size=10_000_000)

        # Send setup message
        setup = {
            "setup": {
                "model": f"models/{model}",
                "generation_config": {
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {
                                "voice_name": config.voice_id or "Puck",
                            }
                        }
                    },
                },
                "system_instruction": {
                    "parts": [{"text": config.system_prompt}],
                },
            }
        }

        if config.tools:
            setup["setup"]["tools"] = [{"function_declarations": config.tools}]

        await self._ws.send(json.dumps(setup))

        # Wait for setup complete
        raw = await self._ws.recv()
        msg = json.loads(raw)
        if "setupComplete" not in msg:
            logger.warning("google_setup_unexpected", msg=msg)

        self._receive_task = asyncio.create_task(self._receive_loop())

        # Send greeting as initial text turn
        if config.greeting:
            await self._ws.send(json.dumps({
                "client_content": {
                    "turns": [{"role": "model", "parts": [{"text": config.greeting}]}],
                    "turn_complete": True,
                }
            }))

        logger.info("google_live_session_started", call_id=config.call_id, model=model)

    async def send_audio(self, audio_chunk: bytes) -> None:
        if not self._ws:
            return

        pcm16k, self._input_resample_state = ulaw_8k_to_pcm16_16k(audio_chunk, self._input_resample_state)
        b64_audio = base64.b64encode(pcm16k).decode()

        await self._ws.send(json.dumps({
            "realtime_input": {
                "media_chunks": [{
                    "data": b64_audio,
                    "mime_type": "audio/pcm;rate=16000",
                }],
            }
        }))

    async def stop_session(self) -> None:
        if self._receive_task:
            self._receive_task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        logger.info("google_live_session_stopped", call_id=self._config.call_id if self._config else "")

    async def interrupt(self) -> None:
        # Google Gemini handles barge-in natively via server VAD
        pass

    async def _receive_loop(self) -> None:
        try:
            async for raw_msg in self._ws:
                try:
                    msg = json.loads(raw_msg)
                    await self._handle_event(msg)
                except json.JSONDecodeError:
                    continue
        except websockets.exceptions.ConnectionClosed:
            logger.info("google_ws_closed")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            ai_agent_provider_errors_total.labels(provider="google_live").inc()
            if self.on_error:
                await self.on_error(e)

    async def _handle_event(self, msg: dict) -> None:
        server_content = msg.get("serverContent")
        if server_content:
            parts = server_content.get("modelTurn", {}).get("parts", [])
            for part in parts:
                if "inlineData" in part:
                    b64_audio = part["inlineData"].get("data", "")
                    if b64_audio:
                        pcm24k = base64.b64decode(b64_audio)
                        ulaw8k, self._output_resample_state = pcm16_24k_to_ulaw_8k(
                            pcm24k, self._output_resample_state
                        )
                        if self.on_audio_output:
                            await self.on_audio_output(ulaw8k)

                if "text" in part:
                    text = part["text"]
                    if text and self.on_transcript:
                        await self.on_transcript("agent", text)

            if server_content.get("turnComplete"):
                if self.on_turn_end:
                    await self.on_turn_end()

        tool_call = msg.get("toolCall")
        if tool_call:
            for fc in tool_call.get("functionCalls", []):
                fn_name = fc.get("name", "")
                fn_args = fc.get("args", {})
                if fn_name and self.on_tool_call:
                    await self.on_tool_call(fn_name, fn_args)
