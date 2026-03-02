"""Turn-taking state machine for AI voice conversations."""

from __future__ import annotations

import asyncio

import structlog

from ai_engine.core.models import CallSession, ConversationState

logger = structlog.get_logger()


class ConversationCoordinator:
    """Manages conversation state transitions and turn-taking logic."""

    def __init__(self, session: CallSession, silence_timeout_ms: int = 5000) -> None:
        self.session = session
        self.silence_timeout_ms = silence_timeout_ms
        self._silence_timer: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def on_greeting_sent(self) -> None:
        async with self._lock:
            self.session.conversation_state = ConversationState.LISTENING
            self._start_silence_timer()
            logger.debug("state_transition", call_id=self.session.call_id, to="listening")

    async def on_speech_start(self) -> None:
        async with self._lock:
            self._cancel_silence_timer()
            self.session.vad_speaking = True

            if self.session.tts_playing:
                self.session.barge_in_count += 1
                logger.debug("barge_in_detected", call_id=self.session.call_id)

            self.session.conversation_state = ConversationState.LISTENING

    async def on_speech_end(self) -> None:
        async with self._lock:
            self.session.vad_speaking = False
            self.session.conversation_state = ConversationState.PROCESSING
            self.session.turn_count += 1
            logger.debug(
                "speech_ended",
                call_id=self.session.call_id,
                turn=self.session.turn_count,
            )

    async def on_agent_speaking(self) -> None:
        async with self._lock:
            self.session.tts_playing = True
            self.session.conversation_state = ConversationState.SPEAKING

    async def on_agent_done_speaking(self) -> None:
        async with self._lock:
            self.session.tts_playing = False
            self.session.conversation_state = ConversationState.LISTENING
            self._start_silence_timer()

    async def on_tool_executing(self) -> None:
        async with self._lock:
            self._cancel_silence_timer()
            self.session.conversation_state = ConversationState.TOOL_EXECUTING

    async def on_tool_complete(self) -> None:
        async with self._lock:
            self.session.conversation_state = ConversationState.PROCESSING

    def _start_silence_timer(self) -> None:
        self._cancel_silence_timer()
        self._silence_timer = asyncio.create_task(self._silence_timeout())

    def _cancel_silence_timer(self) -> None:
        if self._silence_timer and not self._silence_timer.done():
            self._silence_timer.cancel()
            self._silence_timer = None

    async def _silence_timeout(self) -> None:
        try:
            await asyncio.sleep(self.silence_timeout_ms / 1000.0)
            logger.info("silence_timeout", call_id=self.session.call_id)
            if self.on_silence_timeout:
                await self.on_silence_timeout()
        except asyncio.CancelledError:
            pass

    # Callback — set by engine
    on_silence_timeout: asyncio.coroutine | None = None

    async def cleanup(self) -> None:
        self._cancel_silence_timer()
