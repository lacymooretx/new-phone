"""WebSocket handler for FreeSWITCH mod_audio_fork audio streams."""

from __future__ import annotations

import asyncio

import structlog
import websockets
from websockets.server import WebSocketServerProtocol

from ai_engine.core.session_store import session_store

logger = structlog.get_logger()

# Track active WebSocket connections by call_id
_active_connections: dict[str, WebSocketServerProtocol] = {}


async def handle_audio_ws(websocket: WebSocketServerProtocol) -> None:
    """Handle a WebSocket connection from FreeSWITCH mod_audio_fork.

    Path format: /audio/{call_uuid}
    Audio format: raw u-law 8kHz mono frames.
    """
    path = websocket.path
    parts = path.strip("/").split("/")
    if len(parts) < 2 or parts[0] != "audio":
        logger.warning("ws_invalid_path", path=path)
        await websocket.close(1008, "Invalid path")
        return

    call_id = parts[1]
    logger.info("ws_audio_connected", call_id=call_id, remote=str(websocket.remote_address))

    session = await session_store.get(call_id)
    if not session:
        logger.warning("ws_no_session", call_id=call_id)
        await websocket.close(1008, "No active session")
        return

    _active_connections[call_id] = websocket

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                from ai_engine.services.engine import engine
                await engine.process_audio(call_id, message)
            else:
                logger.debug("ws_text_message", call_id=call_id, msg=message[:100])
    except websockets.exceptions.ConnectionClosed:
        logger.info("ws_audio_disconnected", call_id=call_id)
    except Exception as e:
        logger.error("ws_audio_error", call_id=call_id, error=str(e))
    finally:
        _active_connections.pop(call_id, None)
        from ai_engine.services.engine import engine
        await engine.on_audio_stream_ended(call_id)


async def send_audio_to_freeswitch(call_id: str, audio_data: bytes) -> bool:
    """Send audio bytes back to FreeSWITCH via the call's WebSocket."""
    ws = _active_connections.get(call_id)
    if ws is None:
        return False
    try:
        await ws.send(audio_data)
        return True
    except Exception as e:
        logger.error("ws_send_error", call_id=call_id, error=str(e))
        return False


async def start_ws_server(host: str, port: int) -> None:
    """Start the WebSocket server for audio streams."""
    logger.info("ws_server_starting", host=host, port=port)
    async with websockets.serve(handle_audio_ws, host, port):
        logger.info("ws_server_listening", host=host, port=port)
        await asyncio.Future()  # run forever
