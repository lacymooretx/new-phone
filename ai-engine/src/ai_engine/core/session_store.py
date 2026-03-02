"""Async-safe in-memory session store for active AI calls."""

from __future__ import annotations

import asyncio

from ai_engine.core.models import CallSession


class SessionStore:
    """Thread-safe in-memory store for active call sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, CallSession] = {}
        self._lock = asyncio.Lock()

    async def create(self, session: CallSession) -> None:
        async with self._lock:
            self._sessions[session.call_id] = session

    async def get(self, call_id: str) -> CallSession | None:
        async with self._lock:
            return self._sessions.get(call_id)

    async def remove(self, call_id: str) -> CallSession | None:
        async with self._lock:
            return self._sessions.pop(call_id, None)

    async def list_active(self) -> list[CallSession]:
        async with self._lock:
            return list(self._sessions.values())

    async def count(self) -> int:
        async with self._lock:
            return len(self._sessions)


# Singleton
session_store = SessionStore()
