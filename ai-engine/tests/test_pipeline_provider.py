"""Tests for ai_engine.providers.pipeline_provider — PipelineProvider with mocked components."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest
from ai_engine.pipelines.base import LLMChunk, LLMComponent, STTComponent, TTSComponent
from ai_engine.providers.base import ProviderSessionConfig
from ai_engine.providers.pipeline_provider import PipelineProvider, _AudioAccumulator

# ── Fake pipeline components ─────────────────────────────────────────


class _FakeSTT(STTComponent):
    def __init__(self, api_key: str, **kwargs) -> None:
        self._transcripts: list[str] = []

    @property
    def name(self) -> str:
        return "fake_stt"

    async def transcribe_stream(
        self, audio_iter: AsyncIterator[bytes], sample_rate: int
    ) -> AsyncIterator[str]:
        for t in self._transcripts:
            yield t
        # Drain audio iterator
        async for _ in audio_iter:
            pass


class _FakeLLM(LLMComponent):
    def __init__(self, api_key: str, **kwargs) -> None:
        self._response = "Hello from LLM"

    @property
    def name(self) -> str:
        return "fake_llm"

    async def generate(self, messages, tools=None, system_prompt="") -> AsyncIterator[LLMChunk]:
        yield LLMChunk(text=self._response, is_final=True)


class _FakeTTS(TTSComponent):
    def __init__(self, api_key: str, **kwargs) -> None:
        pass

    @property
    def name(self) -> str:
        return "fake_tts"

    async def synthesize(self, text: str, voice_id: str | None = None) -> AsyncIterator[bytes]:
        yield b"\x00" * 320


# ── Tests ─────────────────────────────────────────────────────────────


class TestAudioAccumulator:
    @pytest.mark.asyncio
    async def test_push_and_iterate(self):
        acc = _AudioAccumulator()
        acc.push(b"chunk1")
        acc.push(b"chunk2")
        acc.close()

        chunks = []
        async for c in acc:
            chunks.append(c)
        assert chunks == [b"chunk1", b"chunk2"]

    @pytest.mark.asyncio
    async def test_close_stops_iteration(self):
        acc = _AudioAccumulator()
        acc.close()
        chunks = []
        async for c in acc:
            chunks.append(c)
        assert chunks == []

    @pytest.mark.asyncio
    async def test_push_after_close_ignored(self):
        acc = _AudioAccumulator()
        acc.close()
        acc.push(b"should_be_ignored")
        chunks = []
        async for c in acc:
            chunks.append(c)
        assert chunks == []


class TestPipelineProviderProperties:
    def test_name(self):
        p = PipelineProvider()
        assert p.name == "pipeline"

    def test_capabilities(self):
        p = PipelineProvider()
        caps = p.capabilities
        assert caps.has_native_vad is False
        assert caps.has_native_barge_in is False
        assert caps.is_full_agent is False
        assert "ulaw" in caps.input_encodings


class TestPipelineProviderSession:
    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        provider = PipelineProvider()
        config = ProviderSessionConfig(
            call_id="c1",
            tenant_id="t1",
            api_key="sk-test",
            extra_config={
                "pipeline_stt": "fake",
                "pipeline_llm": "fake",
                "pipeline_tts": "fake",
            },
        )

        with (
            patch("ai_engine.providers.pipeline_provider.create_stt", return_value=_FakeSTT("sk")),
            patch("ai_engine.providers.pipeline_provider.create_llm", return_value=_FakeLLM("sk")),
            patch("ai_engine.providers.pipeline_provider.create_tts", return_value=_FakeTTS("sk")),
        ):
            await provider.start_session(config)
            assert provider._stt is not None
            assert provider._llm is not None
            assert provider._tts is not None
            assert provider._audio_acc is not None

            await provider.stop_session()
            assert provider._cancelled is True

    @pytest.mark.asyncio
    async def test_send_audio(self):
        provider = PipelineProvider()
        config = ProviderSessionConfig(
            call_id="c1",
            tenant_id="t1",
            api_key="sk-test",
            extra_config={},
        )

        with (
            patch("ai_engine.providers.pipeline_provider.create_stt", return_value=_FakeSTT("sk")),
            patch("ai_engine.providers.pipeline_provider.create_llm", return_value=_FakeLLM("sk")),
            patch("ai_engine.providers.pipeline_provider.create_tts", return_value=_FakeTTS("sk")),
        ):
            await provider.start_session(config)
            # send_audio should not raise
            await provider.send_audio(b"\x7f" * 160)
            await provider.stop_session()

    @pytest.mark.asyncio
    async def test_send_audio_before_start(self):
        provider = PipelineProvider()
        # Should silently return when _audio_acc is None
        await provider.send_audio(b"\x7f" * 160)

    @pytest.mark.asyncio
    async def test_interrupt(self):
        provider = PipelineProvider()
        config = ProviderSessionConfig(
            call_id="c1",
            tenant_id="t1",
            api_key="sk-test",
            extra_config={},
        )

        with (
            patch("ai_engine.providers.pipeline_provider.create_stt", return_value=_FakeSTT("sk")),
            patch("ai_engine.providers.pipeline_provider.create_llm", return_value=_FakeLLM("sk")),
            patch("ai_engine.providers.pipeline_provider.create_tts", return_value=_FakeTTS("sk")),
        ):
            await provider.start_session(config)
            # interrupt should set and then reset _cancelled
            await provider.interrupt()
            assert provider._cancelled is False
            await provider.stop_session()

    @pytest.mark.asyncio
    async def test_greeting(self):
        provider = PipelineProvider()
        config = ProviderSessionConfig(
            call_id="c1",
            tenant_id="t1",
            api_key="sk-test",
            greeting="Welcome!",
            extra_config={},
        )

        audio_chunks = []

        async def on_audio(audio: bytes) -> None:
            audio_chunks.append(audio)

        provider.on_audio_output = on_audio

        with (
            patch("ai_engine.providers.pipeline_provider.create_stt", return_value=_FakeSTT("sk")),
            patch("ai_engine.providers.pipeline_provider.create_llm", return_value=_FakeLLM("sk")),
            patch("ai_engine.providers.pipeline_provider.create_tts", return_value=_FakeTTS("sk")),
        ):
            await provider.start_session(config)
            # Give greeting task time to run
            await asyncio.sleep(0.1)
            await provider.stop_session()

        assert len(audio_chunks) > 0
