"""Main AI engine orchestrator — routes audio through providers and pipelines."""

from __future__ import annotations

import asyncio
from time import time

import structlog

from ai_engine.audio.resampler import ResampleState, ulaw_to_pcm16
from ai_engine.audio.vad_manager import VADManager
from ai_engine.config import settings
from ai_engine.core.conversation_coordinator import ConversationCoordinator
from ai_engine.core.models import CallSession, ConversationState, SessionOutcome
from ai_engine.core.session_store import session_store
from ai_engine.providers.base import AIProviderInterface, ProviderSessionConfig
from ai_engine.services import metrics as m

logger = structlog.get_logger()


class AIEngine:
    """Central orchestrator for AI voice agent calls."""

    def __init__(self) -> None:
        self._providers: dict[str, AIProviderInterface] = {}
        self._coordinators: dict[str, ConversationCoordinator] = {}
        self._vad_managers: dict[str, VADManager] = {}
        self._resample_states: dict[str, ResampleState] = {}

    async def start_call(
        self,
        call_id: str,
        tenant_id: str,
        context_name: str,
        provider_name: str,
        provider_config: ProviderSessionConfig,
        silence_timeout_ms: int = 5000,
        barge_in_enabled: bool = True,
    ) -> None:
        """Initialize a new AI agent call session."""
        session = CallSession(
            call_id=call_id,
            tenant_id=tenant_id,
            context_name=context_name,
            caller_number=provider_config.extra_config.get("caller_number"),
            caller_name=provider_config.extra_config.get("caller_name"),
            provider_name=provider_name,
        )

        await session_store.create(session)

        # Create provider instance
        from ai_engine.providers.factory import create_provider
        provider = create_provider(provider_name)
        self._providers[call_id] = provider

        # Wire callbacks
        provider.on_audio_output = lambda audio: asyncio.create_task(
            self._on_provider_audio(call_id, audio)
        )
        provider.on_transcript = lambda speaker, text: asyncio.create_task(
            self._on_provider_transcript(call_id, speaker, text)
        )
        provider.on_tool_call = lambda name, params: asyncio.create_task(
            self._on_provider_tool_call(call_id, name, params)
        )
        provider.on_turn_end = lambda: asyncio.create_task(
            self._on_provider_turn_end(call_id)
        )
        provider.on_error = lambda e: asyncio.create_task(
            self._on_provider_error(call_id, e)
        )

        # Conversation coordinator
        coordinator = ConversationCoordinator(session, silence_timeout_ms=silence_timeout_ms)
        coordinator.on_silence_timeout = lambda: self._on_silence_timeout(call_id)
        self._coordinators[call_id] = coordinator

        # VAD manager (only needed for providers without native VAD)
        if not provider.capabilities.has_native_vad:
            self._vad_managers[call_id] = VADManager(sample_rate=8000)

        m.ai_agent_active_calls.inc()

        # Start provider session
        await provider.start_session(provider_config)

        logger.info(
            "call_started",
            call_id=call_id,
            tenant_id=tenant_id,
            provider=provider_name,
        )

        # Publish event
        await self._publish_event("call_started", call_id, tenant_id, context_name=context_name)

    async def process_audio(self, call_id: str, raw_audio: bytes) -> None:
        """Process an incoming audio chunk from FreeSWITCH."""
        provider = self._providers.get(call_id)
        if not provider:
            return

        session = await session_store.get(call_id)
        if not session or session.conversation_state == ConversationState.ENDED:
            return

        # VAD processing (for providers without native VAD)
        vad = self._vad_managers.get(call_id)
        if vad:
            pcm = ulaw_to_pcm16(raw_audio)
            state_change = vad.process_frame(pcm)
            coordinator = self._coordinators.get(call_id)
            if coordinator:
                if state_change is True:
                    await coordinator.on_speech_start()
                    if session.tts_playing:
                        await provider.interrupt()
                elif state_change is False:
                    await coordinator.on_speech_end()

        # Forward audio to provider
        await provider.send_audio(raw_audio)

    async def stop_call(self, call_id: str, outcome: SessionOutcome = SessionOutcome.HANGUP) -> None:
        """Stop an active AI agent call."""
        session = await session_store.get(call_id)
        if not session:
            return

        session.end_session(outcome)

        # Stop provider
        provider = self._providers.pop(call_id, None)
        if provider:
            await provider.stop_session()

        # Cleanup coordinator
        coordinator = self._coordinators.pop(call_id, None)
        if coordinator:
            await coordinator.cleanup()

        self._vad_managers.pop(call_id, None)
        self._resample_states.pop(call_id, None)

        m.ai_agent_active_calls.dec()
        m.ai_agent_call_duration_seconds.observe(session.duration_seconds)

        # Persist conversation
        from ai_engine.services.db_logger import persist_conversation
        await persist_conversation(session)

        # Remove session
        await session_store.remove(call_id)

        # Publish event
        await self._publish_event(
            "call_ended",
            call_id,
            session.tenant_id,
            outcome=outcome.value,
            duration_seconds=session.duration_seconds,
            turn_count=session.turn_count,
        )

        logger.info(
            "call_ended",
            call_id=call_id,
            outcome=outcome.value,
            duration=session.duration_seconds,
            turns=session.turn_count,
        )

    async def on_audio_stream_ended(self, call_id: str) -> None:
        """Called when FreeSWITCH WebSocket disconnects (hangup)."""
        await self.stop_call(call_id, SessionOutcome.HANGUP)

    # ── Provider callbacks ────────────────────────────────────────

    async def _on_provider_audio(self, call_id: str, audio: bytes) -> None:
        """Provider produced TTS audio — send back to FreeSWITCH."""
        from ai_engine.audio.ws_handler import send_audio_to_freeswitch
        await send_audio_to_freeswitch(call_id, audio)

        coordinator = self._coordinators.get(call_id)
        if coordinator:
            await coordinator.on_agent_speaking()

    async def _on_provider_transcript(self, call_id: str, speaker: str, text: str) -> None:
        """Provider transcribed speech or generated response text."""
        session = await session_store.get(call_id)
        if session:
            session.add_transcript(speaker, text)

    async def _on_provider_tool_call(self, call_id: str, tool_name: str, params: dict) -> None:
        """Provider requested a tool call."""
        session = await session_store.get(call_id)
        if not session:
            return

        coordinator = self._coordinators.get(call_id)
        if coordinator:
            await coordinator.on_tool_executing()

        entry = session.add_tool_call(tool_name, params)
        m.ai_agent_tool_calls_total.labels(tool_name=tool_name, status="started").inc()

        # Execute tool
        from ai_engine.tools.registry import tool_registry
        try:
            from ai_engine.tools.context import ToolExecutionContext
            ctx = ToolExecutionContext(
                call_id=call_id,
                tenant_id=session.tenant_id,
                caller_number=session.caller_number,
                caller_name=session.caller_name,
                api_base_url=settings.api_base_url,
                session=session,
            )
            result = await tool_registry.execute(tool_name, params, ctx)
            entry.result = result
            entry.duration_ms = int((time() - session.started_at) * 1000) - entry.timestamp_ms
            m.ai_agent_tool_calls_total.labels(tool_name=tool_name, status="success").inc()

            # Handle special tool results
            if tool_name == "transfer" and result.get("success"):
                session.end_session(SessionOutcome.TRANSFERRED, result.get("target"))
                m.ai_agent_transfer_to_human_total.inc()

        except Exception as e:
            entry.result = {"error": str(e)}
            m.ai_agent_tool_calls_total.labels(tool_name=tool_name, status="error").inc()
            logger.error("tool_execution_error", tool=tool_name, error=str(e))
            result = {"error": str(e)}

        if coordinator:
            await coordinator.on_tool_complete()

    async def _on_provider_turn_end(self, call_id: str) -> None:
        """Provider finished a complete turn (response done)."""
        coordinator = self._coordinators.get(call_id)
        if coordinator:
            await coordinator.on_agent_done_speaking()

    async def _on_provider_error(self, call_id: str, error: Exception) -> None:
        """Provider encountered an error."""
        session = await session_store.get(call_id)
        provider_name = session.provider_name if session else "unknown"
        m.ai_agent_provider_errors_total.labels(provider=provider_name).inc()
        logger.error("provider_error", call_id=call_id, error=str(error))

    async def _on_silence_timeout(self, call_id: str) -> None:
        """Silence timeout — end the call."""
        logger.info("silence_timeout_ending_call", call_id=call_id)
        await self.stop_call(call_id, SessionOutcome.TIMEOUT)

    # ── Event publishing ─────────────────────────────────────────

    async def _publish_event(self, event_type: str, call_id: str, tenant_id: str, **kwargs) -> None:
        try:
            from ai_engine.main import redis_client
            if redis_client:
                from ai_engine.services.redis_events import RedisEventPublisher
                publisher = RedisEventPublisher(redis_client)
                if event_type == "call_started":
                    await publisher.publish_call_started(call_id, tenant_id, kwargs.get("context_name", ""))
                elif event_type == "call_ended":
                    await publisher.publish_call_ended(
                        call_id, tenant_id,
                        kwargs.get("outcome", "hangup"),
                        kwargs.get("duration_seconds", 0),
                        kwargs.get("turn_count", 0),
                    )
        except Exception as e:
            logger.error("event_publish_error", event_type=event_type, error=str(e))


# Singleton
engine = AIEngine()
