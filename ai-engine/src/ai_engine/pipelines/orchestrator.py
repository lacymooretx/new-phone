"""Pipeline orchestrator — resolves STT/LLM/TTS components and manages the chain."""

from __future__ import annotations

import structlog

from ai_engine.pipelines.base import LLMComponent, STTComponent, TTSComponent

logger = structlog.get_logger()

# Registry of available pipeline components
_STT_COMPONENTS: dict[str, type[STTComponent]] = {}
_LLM_COMPONENTS: dict[str, type[LLMComponent]] = {}
_TTS_COMPONENTS: dict[str, type[TTSComponent]] = {}


def register_stt(name: str, cls: type[STTComponent]) -> None:
    _STT_COMPONENTS[name] = cls


def register_llm(name: str, cls: type[LLMComponent]) -> None:
    _LLM_COMPONENTS[name] = cls


def register_tts(name: str, cls: type[TTSComponent]) -> None:
    _TTS_COMPONENTS[name] = cls


def create_stt(name: str, api_key: str, **kwargs) -> STTComponent:
    cls = _STT_COMPONENTS.get(name)
    if not cls:
        raise ValueError(f"Unknown STT component: {name}. Available: {list(_STT_COMPONENTS.keys())}")
    return cls(api_key=api_key, **kwargs)


def create_llm(name: str, api_key: str, **kwargs) -> LLMComponent:
    cls = _LLM_COMPONENTS.get(name)
    if not cls:
        raise ValueError(f"Unknown LLM component: {name}. Available: {list(_LLM_COMPONENTS.keys())}")
    return cls(api_key=api_key, **kwargs)


def create_tts(name: str, api_key: str, **kwargs) -> TTSComponent:
    cls = _TTS_COMPONENTS.get(name)
    if not cls:
        raise ValueError(f"Unknown TTS component: {name}. Available: {list(_TTS_COMPONENTS.keys())}")
    return cls(api_key=api_key, **kwargs)


def register_all_components() -> None:
    """Register all available pipeline components."""
    from ai_engine.pipelines.deepgram_stt import DeepgramSTT
    from ai_engine.pipelines.openai_stt import OpenAISTT
    from ai_engine.pipelines.openai_llm import OpenAILLM
    from ai_engine.pipelines.anthropic_llm import AnthropicLLM
    from ai_engine.pipelines.openai_tts import OpenAITTS
    from ai_engine.pipelines.elevenlabs_tts import ElevenLabsTTS

    register_stt("deepgram", DeepgramSTT)
    register_stt("openai_whisper", OpenAISTT)

    register_llm("openai", OpenAILLM)
    register_llm("anthropic", AnthropicLLM)

    register_tts("openai", OpenAITTS)
    register_tts("elevenlabs", ElevenLabsTTS)

    logger.info(
        "pipeline_components_registered",
        stt=list(_STT_COMPONENTS.keys()),
        llm=list(_LLM_COMPONENTS.keys()),
        tts=list(_TTS_COMPONENTS.keys()),
    )
