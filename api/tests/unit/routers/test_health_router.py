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
    with patch.dict(sys.modules, {"new_phone.main": main_mod}):
        yield main_mod


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

        _stub_main_module.redis_client = None
        _stub_main_module.freeswitch_service = None

        with patch("new_phone.routers.health.AppSessionLocal", return_value=mock_session):
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["services"]["postgres"]["status"] == "unhealthy"

    async def test_no_external_services(self, client, _stub_main_module):
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
            assert data["services"]["redis"]["status"] == "not_configured"
            assert data["services"]["freeswitch"]["status"] == "not_configured"

    async def test_redis_unhealthy(self, client, _stub_main_module):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("connection lost"))
        _stub_main_module.redis_client = mock_redis
        _stub_main_module.freeswitch_service = None

        with patch("new_phone.routers.health.AppSessionLocal", return_value=mock_session):
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["services"]["redis"]["status"] == "unhealthy"
