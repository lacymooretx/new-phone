import asyncio
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from redis.asyncio import Redis

from ai_engine.config import settings

logger = structlog.get_logger()

redis_client: Redis | None = None


def configure_logging():
    log_level = settings.log_level.upper()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.dev.ConsoleRenderer()
            if log_level == "DEBUG"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    configure_logging()
    logger.info("ai_engine_starting", ws_port=settings.ws_port, api_port=settings.api_port)

    # Redis
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis_client.ping()
        logger.info("redis_connected")
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))

    # Register builtin tools and pipeline components
    from ai_engine.pipelines.orchestrator import register_all_components
    from ai_engine.tools.registry import register_builtin_tools

    register_builtin_tools()
    register_all_components()
    logger.info("tools_and_pipelines_registered")

    # Start WebSocket audio server in background
    from ai_engine.audio.ws_handler import start_ws_server

    ws_task = asyncio.create_task(start_ws_server(settings.ws_host, settings.ws_port))

    yield

    # Shutdown
    ws_task.cancel()
    if redis_client:
        await redis_client.aclose()
    logger.info("ai_engine_shutdown_complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="New Phone AI Engine",
        description="AI Voice Agent Engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    from ai_engine.api.router import router as control_router

    app.include_router(control_router)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
