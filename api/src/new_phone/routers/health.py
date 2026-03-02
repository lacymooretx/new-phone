from fastapi import APIRouter
from sqlalchemy import text

from new_phone.db.engine import AppSessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint — reports status of all services."""
    checks = {}

    # Postgres
    try:
        async with AppSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = {"status": "healthy"}
    except Exception as e:
        checks["postgres"] = {"status": "unhealthy", "error": str(e)}

    # Redis
    try:
        from new_phone.main import redis_client

        if redis_client:
            await redis_client.ping()
            checks["redis"] = {"status": "healthy"}
        else:
            checks["redis"] = {"status": "not_configured"}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}

    # FreeSWITCH
    try:
        from new_phone.main import freeswitch_service

        if freeswitch_service:
            fs_status = await freeswitch_service.is_healthy()
            checks["freeswitch"] = fs_status
        else:
            checks["freeswitch"] = {"status": "not_configured"}
    except Exception as e:
        checks["freeswitch"] = {"status": "unhealthy", "error": str(e)}

    all_healthy = all(
        c.get("status") == "healthy" or c.get("healthy") is True
        for c in checks.values()
        if c.get("status") != "not_configured"
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": checks,
    }
