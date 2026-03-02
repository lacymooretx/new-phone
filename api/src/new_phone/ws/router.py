import asyncio

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from new_phone.auth.jwt import decode_token

logger = structlog.get_logger()

router = APIRouter()

PING_INTERVAL = 30  # seconds
WS_CLOSE_AUTH_FAILED = 4001


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket, token: str = Query(...)):
    from new_phone.main import connection_manager

    # Authenticate via JWT in query param
    try:
        payload = decode_token(token)
    except JWTError:
        await websocket.close(code=WS_CLOSE_AUTH_FAILED, reason="Invalid or expired token")
        return

    if payload.get("type") != "access":
        await websocket.close(code=WS_CLOSE_AUTH_FAILED, reason="Invalid token type")
        return

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        await websocket.close(code=WS_CLOSE_AUTH_FAILED, reason="Missing tenant_id")
        return

    await websocket.accept()
    connection_manager.connect(tenant_id, websocket)
    logger.info("ws_client_connected", tenant_id=tenant_id, user_id=payload.get("sub"))

    try:
        while True:
            # Server-side ping to detect stale connections
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=PING_INTERVAL)
            except TimeoutError:
                # No client message within interval — send ping
                await websocket.send_json({"event": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("ws_error", error=str(e), tenant_id=tenant_id)
    finally:
        connection_manager.disconnect(tenant_id, websocket)
        logger.info("ws_client_disconnected", tenant_id=tenant_id, user_id=payload.get("sub"))
