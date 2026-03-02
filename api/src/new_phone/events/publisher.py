import json
from datetime import UTC, datetime
from uuid import UUID

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger()


class EventPublisher:
    def __init__(self, redis: Redis):
        self._redis = redis

    async def publish(self, tenant_id: UUID, event_type: str, payload: dict) -> None:
        channel = f"events:{tenant_id}"
        envelope = json.dumps(
            {
                "event": event_type,
                "tenant_id": str(tenant_id),
                "payload": payload,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        await self._redis.publish(channel, envelope)
        logger.debug("event_published", channel=channel, event=event_type)


def get_publisher() -> "EventPublisher":
    from new_phone.main import event_publisher

    if event_publisher is None:
        raise RuntimeError("EventPublisher not initialized")
    return event_publisher
