"""Redis pub/sub event publishing for AI agent events."""

from __future__ import annotations

import json

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger()

CHANNEL_PREFIX = "new_phone:ai_agent:"


class RedisEventPublisher:
    """Publishes AI agent events to Redis pub/sub channels."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def publish_call_started(self, call_id: str, tenant_id: str, context_name: str) -> None:
        await self._publish("call_started", {
            "call_id": call_id,
            "tenant_id": tenant_id,
            "context_name": context_name,
        })

    async def publish_call_ended(
        self,
        call_id: str,
        tenant_id: str,
        outcome: str,
        duration_seconds: int,
        turn_count: int,
    ) -> None:
        await self._publish("call_ended", {
            "call_id": call_id,
            "tenant_id": tenant_id,
            "outcome": outcome,
            "duration_seconds": duration_seconds,
            "turn_count": turn_count,
        })

    async def publish_transcript_update(
        self, call_id: str, tenant_id: str, speaker: str, text: str
    ) -> None:
        await self._publish("transcript", {
            "call_id": call_id,
            "tenant_id": tenant_id,
            "speaker": speaker,
            "text": text,
        })

    async def publish_tool_call(
        self, call_id: str, tenant_id: str, tool_name: str, status: str
    ) -> None:
        await self._publish("tool_call", {
            "call_id": call_id,
            "tenant_id": tenant_id,
            "tool_name": tool_name,
            "status": status,
        })

    async def publish_transfer(
        self, call_id: str, tenant_id: str, target: str
    ) -> None:
        await self._publish("transfer", {
            "call_id": call_id,
            "tenant_id": tenant_id,
            "target": target,
        })

    async def _publish(self, event_type: str, data: dict) -> None:
        channel = f"{CHANNEL_PREFIX}{event_type}"
        try:
            await self.redis.publish(channel, json.dumps(data))
        except Exception as e:
            logger.error("redis_publish_error", event_type=event_type, error=str(e))
