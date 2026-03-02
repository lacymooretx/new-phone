"""Abstract base classes for AI voice agent providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable


class ProviderType(StrEnum):
    OPENAI_REALTIME = "openai_realtime"
    DEEPGRAM = "deepgram"
    GOOGLE_LIVE = "google_live"
    ELEVENLABS = "elevenlabs"


@dataclass
class ProviderCapabilities:
    input_encodings: list[str] = field(default_factory=lambda: ["pcm16"])
    input_sample_rates_hz: list[int] = field(default_factory=lambda: [16000])
    output_encodings: list[str] = field(default_factory=lambda: ["pcm16"])
    output_sample_rates_hz: list[int] = field(default_factory=lambda: [16000])
    is_full_agent: bool = False
    has_native_vad: bool = False
    has_native_barge_in: bool = False


@dataclass
class ProviderSessionConfig:
    call_id: str
    tenant_id: str
    api_key: str
    model_id: str | None = None
    base_url: str | None = None
    system_prompt: str = ""
    greeting: str = ""
    voice_id: str | None = None
    language: str = "en-US"
    tools: list[dict[str, Any]] = field(default_factory=list)
    extra_config: dict[str, Any] = field(default_factory=dict)


class AIProviderInterface(ABC):
    """Abstract base class for all AI voice agent providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'openai_realtime')."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Declare provider audio/feature capabilities."""
        ...

    @abstractmethod
    async def start_session(self, config: ProviderSessionConfig) -> None:
        """Initialize provider session with configuration."""
        ...

    @abstractmethod
    async def send_audio(self, audio_chunk: bytes) -> None:
        """Send an audio chunk to the provider."""
        ...

    @abstractmethod
    async def stop_session(self) -> None:
        """Tear down the provider session."""
        ...

    @abstractmethod
    async def interrupt(self) -> None:
        """Interrupt current TTS output (barge-in)."""
        ...

    # Callbacks set by the engine
    on_audio_output: Callable[[bytes], Any] | None = None
    on_transcript: Callable[[str, str], Any] | None = None  # (speaker, text)
    on_tool_call: Callable[[str, dict], Any] | None = None  # (tool_name, params)
    on_turn_end: Callable[[], Any] | None = None
    on_error: Callable[[Exception], Any] | None = None
