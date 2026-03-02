"""Execution context passed to tools during AI agent calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_engine.core.models import CallSession


@dataclass
class ToolExecutionContext:
    call_id: str
    tenant_id: str
    caller_number: str | None
    caller_name: str | None
    api_base_url: str
    session: CallSession
