"""Shared fixtures and C extension stubs for ai-engine tests.

audioop and webrtcvad require C compilation that may not be available in
all environments, so we inject mocks into sys.modules before any
ai_engine code is imported.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

# ── Stub audioop ──────────────────────────────────────────────────────
_audioop = ModuleType("audioop")
_audioop.ulaw2lin = MagicMock(side_effect=lambda data, width: b"\x00\x00" * len(data))
_audioop.lin2ulaw = MagicMock(side_effect=lambda data, width: b"\x7f" * (len(data) // 2))
_audioop.ratecv = MagicMock(
    side_effect=lambda data, width, nchannels, inrate, outrate, state: (data, state)
)
_audioop.rms = MagicMock(return_value=0.0)
sys.modules["audioop"] = _audioop

# ── Stub webrtcvad ────────────────────────────────────────────────────
_webrtcvad = ModuleType("webrtcvad")


class _FakeVad:
    def __init__(self, aggressiveness: int = 2) -> None:
        self._speech = False

    def is_speech(self, buf: bytes, sample_rate: int) -> bool:
        return self._speech


_webrtcvad.Vad = _FakeVad
sys.modules["webrtcvad"] = _webrtcvad

# ── Now safe to import ai_engine modules ──────────────────────────────
import pytest  # noqa: E402
from ai_engine.core.models import CallSession  # noqa: E402
from ai_engine.tools.context import ToolExecutionContext  # noqa: E402


@pytest.fixture()
def make_session():
    """Factory fixture: create a CallSession with sensible defaults."""

    def _make(**overrides) -> CallSession:
        defaults = {
            "call_id": "test-call-001",
            "tenant_id": "tenant-1",
            "context_name": "main-ivr",
        }
        defaults.update(overrides)
        return CallSession(**defaults)

    return _make


@pytest.fixture()
def make_tool_context(make_session):
    """Factory fixture: create a ToolExecutionContext."""

    def _make(**overrides) -> ToolExecutionContext:
        session = overrides.pop("session", None) or make_session()
        defaults = {
            "call_id": session.call_id,
            "tenant_id": session.tenant_id,
            "caller_number": session.caller_number or "+15551234567",
            "caller_name": session.caller_name or "Test Caller",
            "api_base_url": "http://localhost:8000",
            "session": session,
        }
        defaults.update(overrides)
        return ToolExecutionContext(**defaults)

    return _make


@pytest.fixture()
def fresh_registry():
    """Return a brand-new ToolRegistry (avoids singleton pollution)."""
    from ai_engine.tools.registry import ToolRegistry

    return ToolRegistry()
