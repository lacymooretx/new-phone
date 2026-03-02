import asyncio
import smtplib

import httpx
import structlog
from fastapi import APIRouter
from sqlalchemy import text

from new_phone.config import settings
from new_phone.db.engine import AppSessionLocal

logger = structlog.get_logger()

router = APIRouter(tags=["health"])

# Services categorized by criticality
CRITICAL_SERVICES = {"postgres", "redis", "freeswitch"}
NON_CRITICAL_SERVICES = {"minio", "smtp", "ai_engine", "sms_provider"}

CHECK_TIMEOUT = 5.0  # seconds


async def _check_postgres() -> dict:
    """Check PostgreSQL connectivity."""
    try:
        async with AppSessionLocal() as session:
            await asyncio.wait_for(
                session.execute(text("SELECT 1")),
                timeout=CHECK_TIMEOUT,
            )
        return {"status": "healthy"}
    except TimeoutError:
        return {"status": "unhealthy", "error": "Connection timed out"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_redis() -> dict:
    """Check Redis connectivity."""
    try:
        from new_phone.main import redis_client

        if not redis_client:
            return {"status": "unhealthy", "error": "Redis client not initialized"}
        await asyncio.wait_for(redis_client.ping(), timeout=CHECK_TIMEOUT)
        return {"status": "healthy"}
    except TimeoutError:
        return {"status": "unhealthy", "error": "Connection timed out"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_freeswitch() -> dict:
    """Check FreeSWITCH ESL connectivity."""
    try:
        from new_phone.main import freeswitch_service

        if not freeswitch_service:
            return {"status": "unhealthy", "error": "FreeSWITCH service not initialized"}
        result = await asyncio.wait_for(
            freeswitch_service.is_healthy(),
            timeout=CHECK_TIMEOUT,
        )
        if result.get("healthy") is True:
            return {"status": "healthy", "info": result.get("info", "")}
        return {"status": "unhealthy", "error": result.get("error", "No response")}
    except TimeoutError:
        return {"status": "unhealthy", "error": "Connection timed out"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_minio() -> dict:
    """Check MinIO connectivity by listing buckets."""
    try:
        from new_phone.main import storage_service

        if not storage_service or not storage_service.client:
            return {"status": "degraded", "error": "MinIO client not initialized"}

        # list_buckets is a synchronous call in the minio library
        loop = asyncio.get_running_loop()
        buckets = await asyncio.wait_for(
            loop.run_in_executor(None, storage_service.client.list_buckets),
            timeout=CHECK_TIMEOUT,
        )
        bucket_names = [b.name for b in buckets]
        return {"status": "healthy", "buckets": bucket_names}
    except TimeoutError:
        return {"status": "degraded", "error": "Connection timed out"}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


async def _check_smtp() -> dict:
    """Check SMTP connectivity if configured."""
    if not settings.smtp_host:
        return {"status": "healthy", "note": "SMTP not configured"}

    try:
        loop = asyncio.get_running_loop()

        def _smtp_connect():
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=int(CHECK_TIMEOUT)) as smtp:
                smtp.noop()

        await asyncio.wait_for(
            loop.run_in_executor(None, _smtp_connect),
            timeout=CHECK_TIMEOUT,
        )
        return {"status": "healthy", "host": settings.smtp_host, "port": settings.smtp_port}
    except TimeoutError:
        return {"status": "degraded", "error": "Connection timed out"}
    except (smtplib.SMTPException, OSError) as e:
        return {"status": "degraded", "error": str(e)}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


async def _check_ai_engine() -> dict:
    """Check AI engine connectivity via HTTP health endpoint."""
    ai_engine_url = settings.ai_engine_url.rstrip("/")
    health_url = f"{ai_engine_url}/health"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(CHECK_TIMEOUT)) as client:
            response = await client.get(health_url)
            if response.status_code == 200:
                return {"status": "healthy", "url": ai_engine_url}
            return {
                "status": "degraded",
                "error": f"HTTP {response.status_code}",
                "url": ai_engine_url,
            }
    except httpx.TimeoutException:
        return {"status": "degraded", "error": "Connection timed out", "url": ai_engine_url}
    except Exception as e:
        return {"status": "degraded", "error": str(e), "url": ai_engine_url}


async def _check_sms_provider() -> dict:
    """Check SMS provider connectivity by making a lightweight API call."""
    try:
        # Try ClearlyIP SMS API health check
        async with httpx.AsyncClient(timeout=httpx.Timeout(CHECK_TIMEOUT)) as client:
            response = await client.get("https://sms.clearlyip.com/api/v1/health")
            if response.status_code in (200, 401, 403):
                # 401/403 means the API is reachable but auth is needed — that is fine for a health check
                return {"status": "healthy", "provider": "clearlyip"}
            return {
                "status": "degraded",
                "error": f"HTTP {response.status_code}",
                "provider": "clearlyip",
            }
    except httpx.TimeoutException:
        return {"status": "degraded", "error": "Connection timed out", "provider": "clearlyip"}
    except Exception as e:
        return {"status": "degraded", "error": str(e), "provider": "clearlyip"}


@router.get("/health")
async def health_check():
    """Health check endpoint — reports status of all services concurrently.

    Response categorization:
    - "healthy": all critical services (postgres, redis, freeswitch) are up
    - "degraded": all critical services up, but one or more non-critical services down
    - "unhealthy": one or more critical services are down
    """
    results = await asyncio.gather(
        _check_postgres(),
        _check_redis(),
        _check_freeswitch(),
        _check_minio(),
        _check_smtp(),
        _check_ai_engine(),
        _check_sms_provider(),
        return_exceptions=True,
    )

    service_names = [
        "postgres",
        "redis",
        "freeswitch",
        "minio",
        "smtp",
        "ai_engine",
        "sms_provider",
    ]

    checks = {}
    for name, result in zip(service_names, results, strict=True):
        if isinstance(result, Exception):
            error_status = "unhealthy" if name in CRITICAL_SERVICES else "degraded"
            checks[name] = {"status": error_status, "error": str(result)}
        else:
            checks[name] = result

    # Determine overall status
    critical_statuses = [
        checks[svc].get("status") for svc in CRITICAL_SERVICES if svc in checks
    ]
    has_critical_failure = any(s == "unhealthy" for s in critical_statuses)

    non_critical_statuses = [
        checks[svc].get("status") for svc in NON_CRITICAL_SERVICES if svc in checks
    ]
    has_non_critical_failure = any(s in ("degraded", "unhealthy") for s in non_critical_statuses)

    if has_critical_failure:
        overall = "unhealthy"
    elif has_non_critical_failure:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "services": checks,
    }


@router.get("/health/live")
async def liveness():
    """Lightweight liveness probe — just confirms the API process is running."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness():
    """Readiness probe — checks critical services only (postgres, redis)."""
    pg, redis_check = await asyncio.gather(
        _check_postgres(),
        _check_redis(),
        return_exceptions=True,
    )

    ready = True
    services = {}

    for name, result in [("postgres", pg), ("redis", redis_check)]:
        if isinstance(result, Exception):
            services[name] = {"status": "unhealthy", "error": str(result)}
            ready = False
        else:
            services[name] = result
            if result.get("status") != "healthy":
                ready = False

    return {
        "status": "ready" if ready else "not_ready",
        "services": services,
    }
