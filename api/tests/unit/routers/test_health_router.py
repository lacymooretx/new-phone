"""Tests for new_phone.routers.health — health check endpoint."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from new_phone.routers import health


@pytest.fixture
def app():
    """Minimal FastAPI app with just the health router."""
    test_app = FastAPI()
    test_app.include_router(health.router, prefix="/api/v1")
    return test_app


@pytest.fixture(autouse=True)
def _stub_main_module():
    """Ensure new_phone.main is importable with stub globals."""
    main_mod = MagicMock()
    main_mod.redis_client = None
    main_mod.freeswitch_service = None
    main_mod.storage_service = None
    with patch.dict(sys.modules, {"new_phone.main": main_mod}):
        yield main_mod


@pytest.fixture(autouse=True)
def _mock_external_checks():
    """Mock external HTTP and SMTP checks so they don't make real connections."""
    with (
        patch("new_phone.routers.health._check_minio", new_callable=AsyncMock, return_value={"status": "healthy"}),
        patch("new_phone.routers.health._check_smtp", new_callable=AsyncMock, return_value={"status": "healthy"}),
        patch("new_phone.routers.health._check_ai_engine", new_callable=AsyncMock, return_value={"status": "healthy"}),
        patch("new_phone.routers.health._check_sms_provider", new_callable=AsyncMock, return_value={"status": "healthy"}),
    ):
        yield


class TestHealthEndpoint:
    async def test_all_healthy(self, client, _stub_main_module):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        _stub_main_module.redis_client = mock_redis

        mock_fs = AsyncMock()
        mock_fs.is_healthy = AsyncMock(return_value={"healthy": True, "status": "healthy"})
        _stub_main_module.freeswitch_service = mock_fs

        with patch("new_phone.routers.health.AppSessionLocal", return_value=mock_session):
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert data["services"]["postgres"]["status"] == "healthy"
            assert data["services"]["redis"]["status"] == "healthy"

    async def test_postgres_unhealthy(self, client, _stub_main_module):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(side_effect=Exception("connection refused"))

        # Redis and FS healthy
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        _stub_main_module.redis_client = mock_redis
        mock_fs = AsyncMock()
        mock_fs.is_healthy = AsyncMock(return_value={"healthy": True})
        _stub_main_module.freeswitch_service = mock_fs

        with patch("new_phone.routers.health.AppSessionLocal", return_value=mock_session):
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["postgres"]["status"] == "unhealthy"

    async def test_critical_services_not_initialized(self, client, _stub_main_module):
        """When redis and freeswitch are None (not initialized), status is unhealthy."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock()

        _stub_main_module.redis_client = None
        _stub_main_module.freeswitch_service = None

        with patch("new_phone.routers.health.AppSessionLocal", return_value=mock_session):
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["services"]["redis"]["status"] == "unhealthy"
            assert data["services"]["freeswitch"]["status"] == "unhealthy"
            assert data["status"] == "unhealthy"

    async def test_redis_unhealthy(self, client, _stub_main_module):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("connection lost"))
        _stub_main_module.redis_client = mock_redis

        mock_fs = AsyncMock()
        mock_fs.is_healthy = AsyncMock(return_value={"healthy": True})
        _stub_main_module.freeswitch_service = mock_fs

        with patch("new_phone.routers.health.AppSessionLocal", return_value=mock_session):
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["redis"]["status"] == "unhealthy"

    async def test_degraded_when_noncritical_down(self, client, _stub_main_module):
        """When all critical services are up but a non-critical is down, status is degraded."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        _stub_main_module.redis_client = mock_redis
        mock_fs = AsyncMock()
        mock_fs.is_healthy = AsyncMock(return_value={"healthy": True})
        _stub_main_module.freeswitch_service = mock_fs

        with (
            patch("new_phone.routers.health.AppSessionLocal", return_value=mock_session),
            patch("new_phone.routers.health._check_minio", new_callable=AsyncMock, return_value={"status": "degraded", "error": "timeout"}),
        ):
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded"


class TestLivenessEndpoint:
    async def test_alive(self, client):
        resp = await client.get("/api/v1/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"


class TestReadinessEndpoint:
    async def test_ready_when_critical_up(self, client, _stub_main_module):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        _stub_main_module.redis_client = mock_redis

        with patch("new_phone.routers.health.AppSessionLocal", return_value=mock_session):
            resp = await client.get("/api/v1/health/ready")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ready"

    async def test_not_ready_when_redis_down(self, client, _stub_main_module):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock()

        _stub_main_module.redis_client = None

        with patch("new_phone.routers.health.AppSessionLocal", return_value=mock_session):
            resp = await client.get("/api/v1/health/ready")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "not_ready"
