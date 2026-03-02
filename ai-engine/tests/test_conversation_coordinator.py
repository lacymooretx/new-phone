"""Tests for ai_engine.core.conversation_coordinator — state machine + silence timer."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from ai_engine.core.conversation_coordinator import ConversationCoordinator
from ai_engine.core.models import CallSession, ConversationState


@pytest.fixture()
def session():
    return CallSession(call_id="cc-test", tenant_id="t1", context_name="ivr")


@pytest.fixture()
def coordinator(session):
    return ConversationCoordinator(session, silence_timeout_ms=50)


class TestStateTransitions:
    @pytest.mark.asyncio
    async def test_initial_state(self, session):
        assert session.conversation_state == ConversationState.GREETING

    @pytest.mark.asyncio
    async def test_greeting_to_listening(self, coordinator, session):
        await coordinator.on_greeting_sent()
        assert session.conversation_state == ConversationState.LISTENING

    @pytest.mark.asyncio
    async def test_speech_start_sets_listening(self, coordinator, session):
        await coordinator.on_greeting_sent()
        await coordinator.on_speech_start()
        assert session.conversation_state == ConversationState.LISTENING
        assert session.vad_speaking is True

    @pytest.mark.asyncio
    async def test_speech_end_sets_processing(self, coordinator, session):
        await coordinator.on_greeting_sent()
        await coordinator.on_speech_start()
        await coordinator.on_speech_end()
        assert session.conversation_state == ConversationState.PROCESSING
        assert session.vad_speaking is False
        assert session.turn_count == 1

    @pytest.mark.asyncio
    async def test_agent_speaking(self, coordinator, session):
        await coordinator.on_agent_speaking()
        assert session.conversation_state == ConversationState.SPEAKING
        assert session.tts_playing is True

    @pytest.mark.asyncio
    async def test_agent_done_speaking(self, coordinator, session):
        await coordinator.on_agent_speaking()
        await coordinator.on_agent_done_speaking()
        assert session.conversation_state == ConversationState.LISTENING
        assert session.tts_playing is False

    @pytest.mark.asyncio
    async def test_tool_executing(self, coordinator, session):
        await coordinator.on_tool_executing()
        assert session.conversation_state == ConversationState.TOOL_EXECUTING

    @pytest.mark.asyncio
    async def test_tool_complete(self, coordinator, session):
        await coordinator.on_tool_executing()
        await coordinator.on_tool_complete()
        assert session.conversation_state == ConversationState.PROCESSING


class TestBargeIn:
    @pytest.mark.asyncio
    async def test_barge_in_detected(self, coordinator, session):
        await coordinator.on_agent_speaking()
        assert session.tts_playing is True
        await coordinator.on_speech_start()
        assert session.barge_in_count == 1

    @pytest.mark.asyncio
    async def test_no_barge_in_when_not_speaking(self, coordinator, session):
        await coordinator.on_greeting_sent()
        await coordinator.on_speech_start()
        assert session.barge_in_count == 0

    @pytest.mark.asyncio
    async def test_multiple_barge_ins(self, coordinator, session):
        await coordinator.on_agent_speaking()
        await coordinator.on_speech_start()
        await coordinator.on_speech_end()
        await coordinator.on_agent_speaking()
        await coordinator.on_speech_start()
        assert session.barge_in_count == 2


class TestTurnCount:
    @pytest.mark.asyncio
    async def test_increments_on_speech_end(self, coordinator, session):
        await coordinator.on_greeting_sent()
        for _ in range(3):
            await coordinator.on_speech_start()
            await coordinator.on_speech_end()
        assert session.turn_count == 3


class TestSilenceTimer:
    @pytest.mark.asyncio
    async def test_silence_timeout_fires(self, coordinator, session):
        callback = AsyncMock()
        coordinator.on_silence_timeout = callback
        await coordinator.on_greeting_sent()
        # Wait for 50ms timeout + buffer
        await asyncio.sleep(0.15)
        callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_speech_cancels_silence_timer(self, coordinator, session):
        callback = AsyncMock()
        coordinator.on_silence_timeout = callback
        await coordinator.on_greeting_sent()
        # Start speech before timeout
        await asyncio.sleep(0.02)
        await coordinator.on_speech_start()
        await asyncio.sleep(0.1)
        callback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_agent_done_speaking_restarts_timer(self, coordinator, session):
        callback = AsyncMock()
        coordinator.on_silence_timeout = callback
        await coordinator.on_agent_speaking()
        await coordinator.on_agent_done_speaking()
        # Should start new timer
        await asyncio.sleep(0.15)
        callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_tool_executing_cancels_timer(self, coordinator, session):
        callback = AsyncMock()
        coordinator.on_silence_timeout = callback
        await coordinator.on_greeting_sent()
        await asyncio.sleep(0.02)
        await coordinator.on_tool_executing()
        await asyncio.sleep(0.1)
        callback.assert_not_awaited()


class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_cancels_timer(self, coordinator, session):
        callback = AsyncMock()
        coordinator.on_silence_timeout = callback
        await coordinator.on_greeting_sent()
        await coordinator.cleanup()
        await asyncio.sleep(0.1)
        callback.assert_not_awaited()
