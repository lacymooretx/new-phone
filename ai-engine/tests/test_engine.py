"""Tests for ai_engine.services.engine — AIEngine start/stop/process_audio/callbacks."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from ai_engine.core.models import CallSession, ConversationState, SessionOutcome
from ai_engine.providers.base import (
    AIProviderInterface,
    ProviderCapabilities,
    ProviderSessionConfig,
)
from ai_engine.services.engine import AIEngine


class _MockProvider(AIProviderInterface):
    """Minimal mock provider for engine tests."""

    def __init__(self, has_native_vad: bool = False) -> None:
        self._started = False
        self._stopped = False
        self._audio_chunks: list[bytes] = []
        self._interrupted = False
        self._has_native_vad = has_native_vad

    @property
    def name(self) -> str:
        return "mock_provider"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(has_native_vad=self._has_native_vad)

    async def start_session(self, config: ProviderSessionConfig) -> None:
        self._started = True

    async def send_audio(self, audio_chunk: bytes) -> None:
        self._audio_chunks.append(audio_chunk)

    async def stop_session(self) -> None:
        self._stopped = True

    async def interrupt(self) -> None:
        self._interrupted = True


@pytest.fixture()
def engine():
    return AIEngine()


@pytest.fixture()
def provider():
    return _MockProvider()


@pytest.fixture()
def config():
    return ProviderSessionConfig(
        call_id="test-call",
        tenant_id="t1",
        api_key="sk-test",
        extra_config={},
    )


class TestStartCall:
    @pytest.mark.asyncio
    async def test_start_call_creates_session(self, engine, config):
        mock_provider = _MockProvider()

        with (
            patch("ai_engine.providers.factory.create_provider", return_value=mock_provider),
            patch("ai_engine.services.engine.session_store") as mock_store,
            patch("ai_engine.services.engine.m"),
        ):
            mock_store.create = AsyncMock()
            mock_store.get = AsyncMock(return_value=None)

            await engine.start_call(
                call_id="c1",
                tenant_id="t1",
                context_name="ivr",
                provider_name="mock",
                provider_config=config,
            )

        mock_store.create.assert_awaited_once()
        assert mock_provider._started is True

    @pytest.mark.asyncio
    async def test_start_call_wires_callbacks(self, engine, config):
        mock_provider = _MockProvider()

        with (
            patch("ai_engine.providers.factory.create_provider", return_value=mock_provider),
            patch("ai_engine.services.engine.session_store") as mock_store,
            patch("ai_engine.services.engine.m"),
        ):
            mock_store.create = AsyncMock()
            mock_store.get = AsyncMock(return_value=None)

            await engine.start_call(
                call_id="c1",
                tenant_id="t1",
                context_name="ivr",
                provider_name="mock",
                provider_config=config,
            )

        assert mock_provider.on_audio_output is not None
        assert mock_provider.on_transcript is not None
        assert mock_provider.on_tool_call is not None
        assert mock_provider.on_turn_end is not None
        assert mock_provider.on_error is not None

    @pytest.mark.asyncio
    async def test_start_call_creates_vad_for_non_native(self, engine, config):
        mock_provider = _MockProvider(has_native_vad=False)

        with (
            patch("ai_engine.providers.factory.create_provider", return_value=mock_provider),
            patch("ai_engine.services.engine.session_store") as mock_store,
            patch("ai_engine.services.engine.m"),
        ):
            mock_store.create = AsyncMock()

            await engine.start_call(
                call_id="c1",
                tenant_id="t1",
                context_name="ivr",
                provider_name="mock",
                provider_config=config,
            )

        assert "c1" in engine._vad_managers

    @pytest.mark.asyncio
    async def test_start_call_skips_vad_for_native(self, engine, config):
        mock_provider = _MockProvider(has_native_vad=True)

        with (
            patch("ai_engine.providers.factory.create_provider", return_value=mock_provider),
            patch("ai_engine.services.engine.session_store") as mock_store,
            patch("ai_engine.services.engine.m"),
        ):
            mock_store.create = AsyncMock()

            await engine.start_call(
                call_id="c1",
                tenant_id="t1",
                context_name="ivr",
                provider_name="mock",
                provider_config=config,
            )

        assert "c1" not in engine._vad_managers


class TestStopCall:
    @pytest.mark.asyncio
    async def test_stop_call(self, engine, config):
        session = CallSession(call_id="c1", tenant_id="t1", context_name="ivr")
        mock_provider = _MockProvider()
        engine._providers["c1"] = mock_provider

        coordinator = AsyncMock()
        coordinator.cleanup = AsyncMock()
        engine._coordinators["c1"] = coordinator

        with (
            patch("ai_engine.services.engine.session_store") as mock_store,
            patch("ai_engine.services.engine.m"),
            patch("ai_engine.services.db_logger.persist_conversation", new_callable=AsyncMock),
        ):
            mock_store.get = AsyncMock(return_value=session)
            mock_store.remove = AsyncMock()

            await engine.stop_call("c1")

        assert mock_provider._stopped is True
        coordinator.cleanup.assert_awaited_once()
        mock_store.remove.assert_awaited_once_with("c1")

    @pytest.mark.asyncio
    async def test_stop_call_no_session(self, engine):
        with patch("ai_engine.services.engine.session_store") as mock_store:
            mock_store.get = AsyncMock(return_value=None)
            # Should not raise
            await engine.stop_call("nonexistent")

    @pytest.mark.asyncio
    async def test_on_audio_stream_ended(self, engine):
        with patch.object(engine, "stop_call", new_callable=AsyncMock) as mock_stop:
            await engine.on_audio_stream_ended("c1")
            mock_stop.assert_awaited_once_with("c1", SessionOutcome.HANGUP)


class TestProcessAudio:
    @pytest.mark.asyncio
    async def test_process_audio_forwards_to_provider(self, engine):
        session = CallSession(call_id="c1", tenant_id="t1", context_name="ivr")
        mock_provider = _MockProvider()
        engine._providers["c1"] = mock_provider

        with patch("ai_engine.services.engine.session_store") as mock_store:
            mock_store.get = AsyncMock(return_value=session)

            await engine.process_audio("c1", b"\x7f" * 160)

        assert len(mock_provider._audio_chunks) == 1

    @pytest.mark.asyncio
    async def test_process_audio_no_provider(self, engine):
        # Should silently return
        await engine.process_audio("nonexistent", b"\x7f" * 160)

    @pytest.mark.asyncio
    async def test_process_audio_ended_session(self, engine):
        session = CallSession(call_id="c1", tenant_id="t1", context_name="ivr")
        session.conversation_state = ConversationState.ENDED
        mock_provider = _MockProvider()
        engine._providers["c1"] = mock_provider

        with patch("ai_engine.services.engine.session_store") as mock_store:
            mock_store.get = AsyncMock(return_value=session)

            await engine.process_audio("c1", b"\x7f" * 160)

        assert len(mock_provider._audio_chunks) == 0


class TestCallbacks:
    @pytest.mark.asyncio
    async def test_on_provider_transcript(self, engine):
        session = CallSession(call_id="c1", tenant_id="t1", context_name="ivr")

        with patch("ai_engine.services.engine.session_store") as mock_store:
            mock_store.get = AsyncMock(return_value=session)

            await engine._on_provider_transcript("c1", "caller", "Hello")

        assert len(session.transcript) == 1
        assert session.transcript[0].text == "Hello"

    @pytest.mark.asyncio
    async def test_on_provider_error(self, engine):
        session = CallSession(
            call_id="c1", tenant_id="t1", context_name="ivr", provider_name="test"
        )

        with (
            patch("ai_engine.services.engine.session_store") as mock_store,
            patch("ai_engine.services.engine.m"),
        ):
            mock_store.get = AsyncMock(return_value=session)
            # Should not raise
            await engine._on_provider_error("c1", RuntimeError("test error"))

    @pytest.mark.asyncio
    async def test_on_silence_timeout(self, engine):
        with patch.object(engine, "stop_call", new_callable=AsyncMock) as mock_stop:
            await engine._on_silence_timeout("c1")
            mock_stop.assert_awaited_once_with("c1", SessionOutcome.TIMEOUT)

    @pytest.mark.asyncio
    async def test_on_provider_turn_end(self, engine):
        coordinator = AsyncMock()
        coordinator.on_agent_done_speaking = AsyncMock()
        engine._coordinators["c1"] = coordinator

        await engine._on_provider_turn_end("c1")
        coordinator.on_agent_done_speaking.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_provider_audio(self, engine):
        coordinator = AsyncMock()
        coordinator.on_agent_speaking = AsyncMock()
        engine._coordinators["c1"] = coordinator

        with patch(
            "ai_engine.audio.ws_handler.send_audio_to_freeswitch", new_callable=AsyncMock
        ) as mock_send:
            await engine._on_provider_audio("c1", b"\x00" * 320)
            mock_send.assert_awaited_once_with("c1", b"\x00" * 320)
            coordinator.on_agent_speaking.assert_awaited_once()
