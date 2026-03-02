import asyncio
import contextlib

import structlog
from fastapi import WebSocket
from redis.asyncio import Redis

logger = structlog.get_logger()


class ConnectionManager:
    def __init__(self, redis: Redis):
        self._redis = redis
        self._connections: dict[str, set[WebSocket]] = {}
        self._subscriber_task: asyncio.Task | None = None

    def connect(self, tenant_id: str, websocket: WebSocket) -> None:
        if tenant_id not in self._connections:
            self._connections[tenant_id] = set()
        self._connections[tenant_id].add(websocket)
        logger.info("ws_connected", tenant_id=tenant_id, total=len(self._connections[tenant_id]))

    def disconnect(self, tenant_id: str, websocket: WebSocket) -> None:
        conns = self._connections.get(tenant_id)
        if conns:
            conns.discard(websocket)
            if not conns:
                del self._connections[tenant_id]
        logger.info("ws_disconnected", tenant_id=tenant_id)

    async def broadcast(self, tenant_id: str, message: str) -> None:
        conns = self._connections.get(tenant_id)
        if not conns:
            return
        stale: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            conns.discard(ws)
        if not conns:
            self._connections.pop(tenant_id, None)

    async def start_subscriber(self) -> None:
        self._subscriber_task = asyncio.create_task(self._subscribe_loop())
        logger.info("ws_subscriber_started")

    async def stop_subscriber(self) -> None:
        if self._subscriber_task:
            self._subscriber_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._subscriber_task
            self._subscriber_task = None
        logger.info("ws_subscriber_stopped")

    async def _subscribe_loop(self) -> None:
        pubsub = self._redis.pubsub()
        await pubsub.psubscribe("events:*")
        try:
            async for msg in pubsub.listen():
                if msg["type"] != "pmessage":
                    continue
                channel: str = msg["channel"]
                # channel format: "events:<tenant_id>"
                tenant_id = channel.split(":", 1)[1] if ":" in channel else None
                if tenant_id:
                    await self.broadcast(tenant_id, msg["data"])
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.punsubscribe("events:*")
            await pubsub.aclose()
