"""PipelineProvider — wraps modular STT→LLM→TTS chain as an AIProviderInterface.

This allows the engine to handle pipeline mode identically to monolithic mode.
Audio flows: send_audio() → STT → LLM → TTS → on_audio_output callback.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from typing import Any

import structlog

from ai_engine.audio.resampler import ulaw_to_pcm16
from ai_engine.pipelines.orchestrator import create_llm, create_stt, create_tts
from ai_engine.providers.base import (
    AIProviderInterface,
    ProviderCapabilities,
    ProviderSessionConfig,
)

logger = structlog.get_logger()


class _AudioAccumulator:
    """Collects audio chunks and yields them as an async iterator for STT."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._closed = False

    def push(self, chunk: bytes) -> None:
        if not self._closed:
            self._queue.put_nowait(chunk)

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._queue.put_nowait(None)

    async def __aiter__(self) -> AsyncIterator[bytes]:
        while True:
            chunk = await self._queue.get()
            if chunk is None:
                break
            yield chunk


class PipelineProvider(AIProviderInterface):
    """Wraps STT + LLM + TTS pipeline components as a unified provider."""

    def __init__(self) -> None:
        self._stt = None
        self._llm = None
        self._tts = None
        self._config: ProviderSessionConfig | None = None
        self._audio_acc: _AudioAccumulator | None = None
        self._stt_task: asyncio.Task[None] | None = None
        self._conversation_history: list[dict[str, str]] = []
        self._cancelled = False
        self._active_tts_task: asyncio.Task[None] | None = None
        self._greeting_task: asyncio.Task[None] | None = None

    @property
    def name(self) -> str:
        return "pipeline"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            input_encodings=["ulaw"],
            input_sample_rates_hz=[8000],
            output_encodings=["pcm16"],
            output_sample_rates_hz=[8000],
            is_full_agent=False,
            has_native_vad=False,
            has_native_barge_in=False,
        )

    async def start_session(self, config: ProviderSessionConfig) -> None:
        self._config = config
        self._cancelled = False
        self._conversation_history = []

        # Extract pipeline component names and keys from extra_config
        extra = config.extra_config
        stt_name = extra.get("pipeline_stt", "deepgram")
        llm_name = extra.get("pipeline_llm", "openai")
        tts_name = extra.get("pipeline_tts", "openai")
        stt_key = extra.get("stt_api_key", config.api_key)
        llm_key = extra.get("llm_api_key", config.api_key)
        tts_key = extra.get("tts_api_key", config.api_key)

        # Create pipeline components
        self._stt = create_stt(stt_name, stt_key, language=config.language)

        llm_kwargs: dict[str, Any] = {}
        if config.model_id:
            llm_kwargs["model"] = config.model_id
        self._llm = create_llm(llm_name, llm_key, **llm_kwargs)

        tts_kwargs: dict[str, Any] = {}
        if config.voice_id:
            tts_kwargs["voice"] = config.voice_id
        self._tts = create_tts(tts_name, tts_key, **tts_kwargs)

        # Start audio accumulator and STT listener
        self._audio_acc = _AudioAccumulator()
        self._stt_task = asyncio.create_task(self._stt_loop())

        logger.info(
            "pipeline_session_started",
            call_id=config.call_id,
            stt=stt_name,
            llm=llm_name,
            tts=tts_name,
        )

        # Send greeting if configured
        if config.greeting:
            self._greeting_task = asyncio.create_task(self._speak(config.greeting))

    async def send_audio(self, audio_chunk: bytes) -> None:
        if self._audio_acc is None:
            return
        pcm16 = ulaw_to_pcm16(audio_chunk)
        self._audio_acc.push(pcm16)

    async def stop_session(self) -> None:
        self._cancelled = True

        if self._audio_acc:
            self._audio_acc.close()

        if self._stt_task and not self._stt_task.done():
            self._stt_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stt_task

        if self._active_tts_task and not self._active_tts_task.done():
            self._active_tts_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._active_tts_task

        if self._greeting_task and not self._greeting_task.done():
            self._greeting_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._greeting_task

        # Close pipeline components
        if self._stt:
            await self._stt.close()
        if self._llm:
            await self._llm.close()
        if self._tts:
            await self._tts.close()

        logger.info("pipeline_session_stopped")

    async def interrupt(self) -> None:
        """Cancel current LLM/TTS streaming (barge-in)."""
        self._cancelled = True
        if self._active_tts_task and not self._active_tts_task.done():
            self._active_tts_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._active_tts_task
        # Reset for next turn
        self._cancelled = False

    async def _stt_loop(self) -> None:
        """Listen for STT transcripts and process each through LLM→TTS."""
        if not self._stt or not self._audio_acc or not self._config:
            return

        try:
            async for transcript in self._stt.transcribe_stream(self._audio_acc, sample_rate=8000):
                if self._cancelled:
                    continue
                transcript = transcript.strip()
                if not transcript:
                    continue

                logger.debug("pipeline_stt_transcript", text=transcript)

                if self.on_transcript:
                    await _maybe_await(self.on_transcript("caller", transcript))

                await self._process_turn(transcript)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("pipeline_stt_error", error=str(e))
            if self.on_error:
                await _maybe_await(self.on_error(e))

    async def _process_turn(self, user_text: str) -> None:
        """Send user text to LLM, stream response to TTS."""
        if not self._llm or not self._config:
            return

        self._conversation_history.append({"role": "user", "content": user_text})
        tool_schemas = self._config.tools or None

        response_text = ""
        try:
            async for chunk in self._llm.generate(
                messages=self._conversation_history,
                tools=tool_schemas,
                system_prompt=self._config.system_prompt,
            ):
                if self._cancelled:
                    break

                if chunk.tool_call_name:
                    if self.on_tool_call:
                        args: dict[str, Any] = {}
                        if chunk.tool_call_args:
                            try:
                                args = json.loads(chunk.tool_call_args)
                            except json.JSONDecodeError:
                                args = {"raw": chunk.tool_call_args}
                        await _maybe_await(self.on_tool_call(chunk.tool_call_name, args))
                    continue

                if chunk.text:
                    response_text += chunk.text

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("pipeline_llm_error", error=str(e))
            if self.on_error:
                await _maybe_await(self.on_error(e))
            return

        if self._cancelled or not response_text:
            return

        self._conversation_history.append({"role": "assistant", "content": response_text})

        if self.on_transcript:
            await _maybe_await(self.on_transcript("agent", response_text))

        self._active_tts_task = asyncio.create_task(self._speak(response_text))
        with contextlib.suppress(asyncio.CancelledError):
            await self._active_tts_task

    async def _speak(self, text: str) -> None:
        """Synthesize text to audio and fire on_audio_output callback."""
        if not self._tts or not self._config:
            return

        try:
            async for audio_chunk in self._tts.synthesize(text, self._config.voice_id):
                if self._cancelled:
                    break
                if self.on_audio_output:
                    await _maybe_await(self.on_audio_output(audio_chunk))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("pipeline_tts_error", error=str(e))
            if self.on_error:
                await _maybe_await(self.on_error(e))
            return

        if not self._cancelled and self.on_turn_end:
            await _maybe_await(self.on_turn_end())


async def _maybe_await(result: Any) -> Any:
    """Await a result if it's a coroutine, otherwise return it."""
    if asyncio.iscoroutine(result):
        return await result
    return result
