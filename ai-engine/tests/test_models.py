"""Tests for ai_engine.core.models — CallSession, LatencyAccumulator, enums."""

from __future__ import annotations

from time import time

from ai_engine.core.models import (
    CallSession,
    ConversationState,
    LatencyAccumulator,
    SessionOutcome,
    ToolCallEntry,
    TranscriptEntry,
)


class TestConversationState:
    def test_values(self):
        assert ConversationState.GREETING == "greeting"
        assert ConversationState.LISTENING == "listening"
        assert ConversationState.PROCESSING == "processing"
        assert ConversationState.SPEAKING == "speaking"
        assert ConversationState.TOOL_EXECUTING == "tool_executing"
        assert ConversationState.TRANSFERRING == "transferring"
        assert ConversationState.ENDED == "ended"

    def test_is_str(self):
        assert isinstance(ConversationState.GREETING, str)


class TestSessionOutcome:
    def test_values(self):
        assert SessionOutcome.RESOLVED == "resolved"
        assert SessionOutcome.TRANSFERRED == "transferred"
        assert SessionOutcome.VOICEMAIL == "voicemail"
        assert SessionOutcome.HANGUP == "hangup"
        assert SessionOutcome.TIMEOUT == "timeout"


class TestTranscriptEntry:
    def test_create(self):
        entry = TranscriptEntry(speaker="caller", text="Hello", timestamp_ms=1000)
        assert entry.speaker == "caller"
        assert entry.text == "Hello"
        assert entry.timestamp_ms == 1000


class TestToolCallEntry:
    def test_defaults(self):
        entry = ToolCallEntry(tool_name="transfer", params={"target": "1001"})
        assert entry.result is None
        assert entry.timestamp_ms == 0
        assert entry.duration_ms == 0

    def test_full(self):
        entry = ToolCallEntry(
            tool_name="hangup",
            params={},
            result={"success": True},
            timestamp_ms=500,
            duration_ms=50,
        )
        assert entry.result == {"success": True}


class TestLatencyAccumulator:
    def test_empty(self):
        acc = LatencyAccumulator()
        d = acc.to_dict()
        assert d["avg_stt_ms"] == 0.0
        assert d["avg_llm_ms"] == 0.0
        assert d["avg_tts_ms"] == 0.0
        assert d["p95_turn_ms"] == 0.0

    def test_record_and_avg(self):
        acc = LatencyAccumulator()
        acc.record_stt(100.0)
        acc.record_stt(200.0)
        d = acc.to_dict()
        assert d["avg_stt_ms"] == 150.0

    def test_record_llm(self):
        acc = LatencyAccumulator()
        acc.record_llm(50.0)
        acc.record_llm(150.0)
        d = acc.to_dict()
        assert d["avg_llm_ms"] == 100.0

    def test_record_tts(self):
        acc = LatencyAccumulator()
        acc.record_tts(30.0)
        d = acc.to_dict()
        assert d["avg_tts_ms"] == 30.0

    def test_p95(self):
        acc = LatencyAccumulator()
        for i in range(1, 101):
            acc.record_turn(float(i))
        d = acc.to_dict()
        # idx = int(100 * 0.95) = 95, sorted[95] = 96 (1-indexed values)
        assert d["p95_turn_ms"] == 96.0

    def test_p95_single(self):
        acc = LatencyAccumulator()
        acc.record_turn(42.0)
        d = acc.to_dict()
        assert d["p95_turn_ms"] == 42.0


class TestCallSession:
    def test_defaults(self):
        s = CallSession(call_id="c1", tenant_id="t1", context_name="ivr")
        assert s.conversation_state == ConversationState.GREETING
        assert s.outcome == SessionOutcome.HANGUP
        assert s.transcript == []
        assert s.tool_calls == []
        assert s.turn_count == 0
        assert s.barge_in_count == 0
        assert s.vad_speaking is False
        assert s.ended_at is None
        assert s.started_at > 0

    def test_duration_seconds(self):
        s = CallSession(call_id="c1", tenant_id="t1", context_name="ivr")
        s.started_at = time() - 10
        assert s.duration_seconds >= 9  # Allow some rounding

    def test_duration_with_ended_at(self):
        s = CallSession(call_id="c1", tenant_id="t1", context_name="ivr")
        s.started_at = 1000.0
        s.ended_at = 1030.0
        assert s.duration_seconds == 30

    def test_add_transcript(self):
        s = CallSession(call_id="c1", tenant_id="t1", context_name="ivr")
        s.add_transcript("caller", "Hello")
        s.add_transcript("agent", "Hi there")
        assert len(s.transcript) == 2
        assert s.transcript[0].speaker == "caller"
        assert s.transcript[0].text == "Hello"
        assert s.transcript[0].timestamp_ms >= 0

    def test_add_tool_call(self):
        s = CallSession(call_id="c1", tenant_id="t1", context_name="ivr")
        entry = s.add_tool_call("transfer", {"target": "1001"})
        assert isinstance(entry, ToolCallEntry)
        assert entry.tool_name == "transfer"
        assert len(s.tool_calls) == 1

    def test_end_session(self):
        s = CallSession(call_id="c1", tenant_id="t1", context_name="ivr")
        s.end_session(SessionOutcome.TRANSFERRED, transferred_to="1001")
        assert s.outcome == SessionOutcome.TRANSFERRED
        assert s.transferred_to == "1001"
        assert s.conversation_state == ConversationState.ENDED
        assert s.ended_at is not None

    def test_end_session_no_transfer(self):
        s = CallSession(call_id="c1", tenant_id="t1", context_name="ivr")
        s.end_session(SessionOutcome.TIMEOUT)
        assert s.outcome == SessionOutcome.TIMEOUT
        assert s.transferred_to is None
