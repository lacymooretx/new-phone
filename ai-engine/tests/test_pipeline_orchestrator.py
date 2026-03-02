"""Tests for ai_engine.pipelines.orchestrator — component registry + factory."""

from __future__ import annotations

import pytest
from ai_engine.pipelines.base import LLMComponent, STTComponent, TTSComponent
from ai_engine.pipelines.orchestrator import (
    _LLM_COMPONENTS,
    _STT_COMPONENTS,
    _TTS_COMPONENTS,
    create_llm,
    create_stt,
    create_tts,
    register_llm,
    register_stt,
    register_tts,
)


class _FakeSTT(STTComponent):
    def __init__(self, api_key: str, **kwargs) -> None:
        self._api_key = api_key
        self._kwargs = kwargs

    @property
    def name(self) -> str:
        return "fake_stt"

    async def transcribe_stream(self, audio_iter, sample_rate):
        yield "hello"


class _FakeLLM(LLMComponent):
    def __init__(self, api_key: str, **kwargs) -> None:
        self._api_key = api_key
        self._kwargs = kwargs

    @property
    def name(self) -> str:
        return "fake_llm"

    async def generate(self, messages, tools=None, system_prompt=""):
        from ai_engine.pipelines.base import LLMChunk

        yield LLMChunk(text="response")


class _FakeTTS(TTSComponent):
    def __init__(self, api_key: str, **kwargs) -> None:
        self._api_key = api_key
        self._kwargs = kwargs

    @property
    def name(self) -> str:
        return "fake_tts"

    async def synthesize(self, text, voice_id=None):
        yield b"\x00" * 320


@pytest.fixture(autouse=True)
def _clean_registries():
    """Snapshot and restore registries to avoid test pollution."""
    stt_snap = dict(_STT_COMPONENTS)
    llm_snap = dict(_LLM_COMPONENTS)
    tts_snap = dict(_TTS_COMPONENTS)
    yield
    _STT_COMPONENTS.clear()
    _STT_COMPONENTS.update(stt_snap)
    _LLM_COMPONENTS.clear()
    _LLM_COMPONENTS.update(llm_snap)
    _TTS_COMPONENTS.clear()
    _TTS_COMPONENTS.update(tts_snap)


class TestRegister:
    def test_register_stt(self):
        register_stt("test_stt", _FakeSTT)
        assert "test_stt" in _STT_COMPONENTS

    def test_register_llm(self):
        register_llm("test_llm", _FakeLLM)
        assert "test_llm" in _LLM_COMPONENTS

    def test_register_tts(self):
        register_tts("test_tts", _FakeTTS)
        assert "test_tts" in _TTS_COMPONENTS


class TestCreate:
    def test_create_stt(self):
        register_stt("test_stt", _FakeSTT)
        stt = create_stt("test_stt", "sk-test", language="en")
        assert isinstance(stt, _FakeSTT)
        assert stt._api_key == "sk-test"
        assert stt._kwargs == {"language": "en"}

    def test_create_llm(self):
        register_llm("test_llm", _FakeLLM)
        llm = create_llm("test_llm", "sk-test", model="gpt-4")
        assert isinstance(llm, _FakeLLM)
        assert llm._kwargs == {"model": "gpt-4"}

    def test_create_tts(self):
        register_tts("test_tts", _FakeTTS)
        tts = create_tts("test_tts", "sk-test")
        assert isinstance(tts, _FakeTTS)

    def test_create_unknown_stt_raises(self):
        with pytest.raises(ValueError, match="Unknown STT"):
            create_stt("nonexistent", "sk-test")

    def test_create_unknown_llm_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM"):
            create_llm("nonexistent", "sk-test")

    def test_create_unknown_tts_raises(self):
        with pytest.raises(ValueError, match="Unknown TTS"):
            create_tts("nonexistent", "sk-test")
