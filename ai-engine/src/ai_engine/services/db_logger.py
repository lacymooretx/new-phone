"""Persist AI agent conversation data to PostgreSQL."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ai_engine.config import settings
from ai_engine.core.models import CallSession

logger = structlog.get_logger()

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, pool_size=5, max_overflow=5)
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(_get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def persist_conversation(session: CallSession) -> str | None:
    """Write a completed CallSession to the ai_agent_conversations table.

    Uses raw SQL to avoid importing API models into the AI engine service.
    Returns the conversation UUID or None on failure.
    """
    conversation_id = str(uuid.uuid4())
    factory = _get_session_factory()

    transcript_data = [
        {"speaker": t.speaker, "text": t.text, "timestamp_ms": t.timestamp_ms}
        for t in session.transcript
    ]

    tool_calls_data = None
    if session.tool_calls:
        tool_calls_data = [
            {
                "tool_name": tc.tool_name,
                "params": tc.params,
                "result": tc.result,
                "timestamp_ms": tc.timestamp_ms,
            }
            for tc in session.tool_calls
        ]

    latency_data = session.latency.to_dict()

    started_at = datetime.fromtimestamp(session.started_at, tz=UTC)
    ended_at = datetime.fromtimestamp(session.ended_at, tz=UTC) if session.ended_at else None

    try:
        async with factory() as db:
            await db.execute(
                text("""
                    INSERT INTO ai_agent_conversations (
                        id, tenant_id, context_id, call_id, caller_number, caller_name,
                        provider_name, transcript, tool_calls, summary, outcome,
                        transferred_to, duration_seconds, turn_count, barge_in_count,
                        latency_metrics, provider_cost_usd, started_at, ended_at, created_at
                    ) VALUES (
                        :id, :tenant_id, NULL, :call_id, :caller_number, :caller_name,
                        :provider_name, :transcript::jsonb, :tool_calls::jsonb, :summary,
                        :outcome, :transferred_to, :duration_seconds, :turn_count,
                        :barge_in_count, :latency_metrics::jsonb, :provider_cost_usd,
                        :started_at, :ended_at, now()
                    )
                """),
                {
                    "id": conversation_id,
                    "tenant_id": session.tenant_id,
                    "call_id": session.call_id,
                    "caller_number": session.caller_number or "",
                    "caller_name": session.caller_name,
                    "provider_name": session.provider_name,
                    "transcript": _json_dumps(transcript_data),
                    "tool_calls": _json_dumps(tool_calls_data) if tool_calls_data else None,
                    "summary": session.summary,
                    "outcome": session.outcome.value,
                    "transferred_to": session.transferred_to,
                    "duration_seconds": session.duration_seconds,
                    "turn_count": session.turn_count,
                    "barge_in_count": session.barge_in_count,
                    "latency_metrics": _json_dumps(latency_data),
                    "provider_cost_usd": None,
                    "started_at": started_at,
                    "ended_at": ended_at,
                },
            )
            await db.commit()
            logger.info(
                "conversation_persisted",
                conversation_id=conversation_id,
                call_id=session.call_id,
                outcome=session.outcome.value,
            )
            return conversation_id
    except Exception as e:
        logger.error("conversation_persist_error", call_id=session.call_id, error=str(e))
        return None


def _json_dumps(obj) -> str:
    import json
    return json.dumps(obj)
