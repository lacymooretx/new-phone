"""Core data models for AI engine call sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from time import time


class ConversationState(StrEnum):
    GREETING = "greeting"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    TOOL_EXECUTING = "tool_executing"
    TRANSFERRING = "transferring"
    ENDED = "ended"


class SessionOutcome(StrEnum):
    RESOLVED = "resolved"
    TRANSFERRED = "transferred"
    VOICEMAIL = "voicemail"
    HANGUP = "hangup"
    TIMEOUT = "timeout"


@dataclass
class TranscriptEntry:
    speaker: str  # "caller" or "agent"
    text: str
    timestamp_ms: int


@dataclass
class ToolCallEntry:
    tool_name: str
    params: dict
    result: dict | None = None
    timestamp_ms: int = 0
    duration_ms: int = 0


@dataclass
class LatencyAccumulator:
    stt_samples: list[float] = field(default_factory=list)
    llm_samples: list[float] = field(default_factory=list)
    tts_samples: list[float] = field(default_factory=list)
    turn_samples: list[float] = field(default_factory=list)

    def record_stt(self, ms: float) -> None:
        self.stt_samples.append(ms)

    def record_llm(self, ms: float) -> None:
        self.llm_samples.append(ms)

    def record_tts(self, ms: float) -> None:
        self.tts_samples.append(ms)

    def record_turn(self, ms: float) -> None:
        self.turn_samples.append(ms)

    def _avg(self, samples: list[float]) -> float:
        return sum(samples) / len(samples) if samples else 0.0

    def _p95(self, samples: list[float]) -> float:
        if not samples:
            return 0.0
        sorted_s = sorted(samples)
        idx = int(len(sorted_s) * 0.95)
        return sorted_s[min(idx, len(sorted_s) - 1)]

    def to_dict(self) -> dict:
        return {
            "avg_stt_ms": round(self._avg(self.stt_samples), 1),
            "avg_llm_ms": round(self._avg(self.llm_samples), 1),
            "avg_tts_ms": round(self._avg(self.tts_samples), 1),
            "p95_turn_ms": round(self._p95(self.turn_samples), 1),
        }


@dataclass
class CallSession:
    call_id: str
    tenant_id: str
    context_name: str
    caller_number: str | None = None
    caller_name: str | None = None

    # Provider info
    provider_name: str = ""
    provider_mode: str = "monolithic"  # "monolithic" or "pipeline"

    # State
    conversation_state: ConversationState = ConversationState.GREETING
    outcome: SessionOutcome = SessionOutcome.HANGUP
    transferred_to: str | None = None

    # Conversation data
    transcript: list[TranscriptEntry] = field(default_factory=list)
    tool_calls: list[ToolCallEntry] = field(default_factory=list)
    summary: str | None = None

    # Counters
    turn_count: int = 0
    barge_in_count: int = 0
    tts_playing: bool = False

    # Timing
    started_at: float = field(default_factory=time)
    ended_at: float | None = None
    latency: LatencyAccumulator = field(default_factory=LatencyAccumulator)

    # Audio state
    vad_speaking: bool = False

    @property
    def duration_seconds(self) -> int:
        end = self.ended_at or time()
        return int(end - self.started_at)

    def add_transcript(self, speaker: str, text: str) -> None:
        elapsed_ms = int((time() - self.started_at) * 1000)
        self.transcript.append(TranscriptEntry(speaker=speaker, text=text, timestamp_ms=elapsed_ms))

    def add_tool_call(self, tool_name: str, params: dict) -> ToolCallEntry:
        elapsed_ms = int((time() - self.started_at) * 1000)
        entry = ToolCallEntry(tool_name=tool_name, params=params, timestamp_ms=elapsed_ms)
        self.tool_calls.append(entry)
        return entry

    def end_session(self, outcome: SessionOutcome, transferred_to: str | None = None) -> None:
        self.ended_at = time()
        self.outcome = outcome
        self.transferred_to = transferred_to
        self.conversation_state = ConversationState.ENDED
