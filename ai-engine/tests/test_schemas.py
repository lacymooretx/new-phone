"""Tests for ai_engine.api.schemas — Pydantic request/response models."""

from __future__ import annotations

import pytest
from ai_engine.api.schemas import (
    CallStatusResponse,
    StartCallRequest,
    StopCallRequest,
    TestContextRequest,
    TestProviderRequest,
)
from pydantic import ValidationError


class TestStartCallRequest:
    def test_minimal(self):
        req = StartCallRequest(call_id="c1", tenant_id="t1", context_name="ivr")
        assert req.call_id == "c1"
        assert req.provider_mode == "monolithic"
        assert req.provider_name == ""
        assert req.language == "en-US"
        assert req.tools == []
        assert req.barge_in_enabled is True
        assert req.silence_timeout_ms == 5000

    def test_full(self):
        req = StartCallRequest(
            call_id="c2",
            tenant_id="t2",
            context_name="support",
            caller_number="+15551234567",
            caller_name="Jane",
            provider_mode="pipeline",
            provider_name="openai_realtime",
            api_key="sk-test",
            model_id="gpt-4o",
            system_prompt="You are helpful.",
            greeting="Hello!",
            voice_id="alloy",
            language="es-ES",
            tools=["transfer", "hangup"],
            barge_in_enabled=False,
            silence_timeout_ms=3000,
            pipeline_stt="deepgram",
            pipeline_llm="openai",
            pipeline_tts="elevenlabs",
            stt_api_key="sk-stt",
            llm_api_key="sk-llm",
            tts_api_key="sk-tts",
        )
        assert req.caller_name == "Jane"
        assert req.tools == ["transfer", "hangup"]
        assert req.pipeline_stt == "deepgram"

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            StartCallRequest(tenant_id="t1", context_name="ivr")  # missing call_id

    def test_optional_fields_none(self):
        req = StartCallRequest(call_id="c1", tenant_id="t1", context_name="ivr")
        assert req.caller_number is None
        assert req.model_id is None
        assert req.voice_id is None
        assert req.pipeline_stt is None


class TestStopCallRequest:
    def test_valid(self):
        req = StopCallRequest(call_id="c1")
        assert req.call_id == "c1"

    def test_missing_call_id(self):
        with pytest.raises(ValidationError):
            StopCallRequest()


class TestCallStatusResponse:
    def test_defaults(self):
        resp = CallStatusResponse(status="accepted", call_id="c1")
        assert resp.provider is None
        assert resp.duration_seconds == 0
        assert resp.turn_count == 0

    def test_full(self):
        resp = CallStatusResponse(
            status="stopped",
            call_id="c1",
            provider="openai_realtime",
            duration_seconds=120,
            turn_count=5,
        )
        assert resp.provider == "openai_realtime"
        assert resp.turn_count == 5


class TestTestProviderRequest:
    def test_valid(self):
        req = TestProviderRequest(provider_name="openai_realtime", api_key="sk-test")
        assert req.model_id is None

    def test_missing_fields(self):
        with pytest.raises(ValidationError):
            TestProviderRequest(provider_name="deepgram")  # missing api_key


class TestTestContextRequest:
    def test_defaults(self):
        req = TestContextRequest(system_prompt="Be helpful.", message="Hello")
        assert req.provider_name == "openai"
        assert req.api_key == ""

    def test_full(self):
        req = TestContextRequest(
            system_prompt="Help me.",
            message="Hi",
            provider_name="anthropic",
            api_key="sk-ant",
            model_id="claude-sonnet-4-6",
        )
        assert req.model_id == "claude-sonnet-4-6"
