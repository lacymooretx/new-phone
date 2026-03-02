"""Abstract base classes for modular STT/LLM/TTS pipeline components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator


@dataclass
class LLMChunk:
    """A chunk from LLM streaming response."""

    text: str = ""
    tool_call_name: str | None = None
    tool_call_args: str | None = None
    is_final: bool = False


class STTComponent(ABC):
    """Abstract Speech-to-Text component."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def transcribe_stream(
        self, audio_iter: AsyncIterator[bytes], sample_rate: int
    ) -> AsyncIterator[str]:
        """Stream audio frames and yield transcription text chunks."""
        ...

    async def close(self) -> None:
        """Cleanup resources."""
        pass


class LLMComponent(ABC):
    """Abstract LLM component for generating responses."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str = "",
    ) -> AsyncIterator[LLMChunk]:
        """Generate a streaming response given conversation messages."""
        ...

    async def close(self) -> None:
        pass


class TTSComponent(ABC):
    """Abstract Text-to-Speech component."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def synthesize(
        self, text: str, voice_id: str | None = None
    ) -> AsyncIterator[bytes]:
        """Synthesize text to audio, yielding PCM16 chunks."""
        ...

    async def close(self) -> None:
        pass
