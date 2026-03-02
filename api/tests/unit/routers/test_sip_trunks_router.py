"""Tests for new_phone.routers.sip_trunks — Trunk CRUD, provision, deprovision, test."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from new_phone.deps.auth import get_admin_db, get_current_user
from new_phone.routers import sip_trunks

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TRUNK_ID = uuid.UUID("00000000-0000-0000-0000-bbbbbbbbbbbb")


def _make_trunk(**overrides):
    from datetime import UTC, datetime

    defaults = dict(
        id=TRUNK_ID,
        tenant_id=TENANT_ID,
        name="Primary Trunk",
        auth_type="registration",
        host="sip.clearlyip.com",
        port=5061,
        transport="tls",
        username="user",
        ip_acl=None,
        codec_preferences=None,
        max_channels=30,
        inbound_cid_mode="passthrough",
        failover_trunk_id=None,
        notes=None,
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


@pytest.fixture
def app(mock_db, acme_admin_user):
    test_app = FastAPI()
    test_app.include_router(sip_trunks.router, prefix="/api/v1")

    async def override_db():
        yield mock_db

    test_app.dependency_overrides[get_admin_db] = override_db
    test_app.dependency_overrides[get_current_user] = lambda: acme_admin_user
    yield test_app
    test_app.dependency_overrides.clear()


# ── GET list ────────────────────────────────────────────────────────────


class TestListTrunks:
    async def test_success(self, client):
        with patch("new_phone.routers.sip_trunks.SIPTrunkService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.list_trunks = AsyncMock(return_value=[_make_trunk()])

            resp = await client.get(f"/api/v1/tenants/{TENANT_ID}/trunks")
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)
            assert len(resp.json()) == 1


# ── POST create ─────────────────────────────────────────────────────────


class TestCreateTrunk:
    async def test_success_returns_201(self, client):
        with patch("new_phone.routers.sip_trunks.SIPTrunkService") as MockSvc, \
             patch("new_phone.routers.sip_trunks._sync_gateway_create", new_callable=AsyncMock):
            mock_svc = MockSvc.return_value
            mock_svc.create_trunk = AsyncMock(return_value=_make_trunk())

            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/trunks",
                json={
                    "name": "Primary Trunk",
                    "auth_type": "registration",
                    "host": "sip.clearlyip.com",
                    "port": 5061,
                    "transport": "tls",
                },
            )
            assert resp.status_code == 201


# ── GET detail ──────────────────────────────────────────────────────────


class TestGetTrunk:
    async def test_found_returns_200(self, client):
        with patch("new_phone.routers.sip_trunks.SIPTrunkService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_trunk = AsyncMock(return_value=_make_trunk())

            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/trunks/{TRUNK_ID}"
            )
            assert resp.status_code == 200

    async def test_not_found_returns_404(self, client):
        with patch("new_phone.routers.sip_trunks.SIPTrunkService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_trunk = AsyncMock(return_value=None)

            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/trunks/{TRUNK_ID}"
            )
            assert resp.status_code == 404


# ── PATCH update ────────────────────────────────────────────────────────


class TestUpdateTrunk:
    async def test_success_returns_200(self, client):
        with patch("new_phone.routers.sip_trunks.SIPTrunkService") as MockSvc, \
             patch("new_phone.routers.sip_trunks._sync_gateway_change", new_callable=AsyncMock), \
             patch("new_phone.db.engine.AdminSessionLocal") as MockSession:
            mock_svc = MockSvc.return_value
            mock_svc.get_trunk = AsyncMock(return_value=_make_trunk())
            mock_svc.update_trunk = AsyncMock(return_value=_make_trunk(name="Updated"))
            # Mock the AdminSessionLocal context manager
            mock_sess_instance = AsyncMock()
            mock_tenant = MagicMock()
            mock_tenant.slug = "acme"
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_tenant
            mock_sess_instance.execute = AsyncMock(return_value=mock_result)
            MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_sess_instance)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await client.patch(
                f"/api/v1/tenants/{TENANT_ID}/trunks/{TRUNK_ID}",
                json={"name": "Updated Trunk"},
            )
            assert resp.status_code == 200

    async def test_not_found_returns_404(self, client):
        with patch("new_phone.routers.sip_trunks.SIPTrunkService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_trunk = AsyncMock(return_value=_make_trunk())
            mock_svc.update_trunk = AsyncMock(
                side_effect=ValueError("Trunk not found")
            )

            resp = await client.patch(
                f"/api/v1/tenants/{TENANT_ID}/trunks/{TRUNK_ID}",
                json={"name": "Updated Trunk"},
            )
            assert resp.status_code == 404


# ── DELETE deactivate ───────────────────────────────────────────────────


class TestDeactivateTrunk:
    async def test_success_returns_200(self, client):
        with patch("new_phone.routers.sip_trunks.SIPTrunkService") as MockSvc, \
             patch("new_phone.routers.sip_trunks._sync_gateway_change", new_callable=AsyncMock), \
             patch("new_phone.db.engine.AdminSessionLocal") as MockSession:
            mock_svc = MockSvc.return_value
            mock_svc.get_trunk = AsyncMock(return_value=_make_trunk())
            mock_svc.deactivate_trunk = AsyncMock(return_value=_make_trunk(is_active=False))
            # Mock the AdminSessionLocal context manager
            mock_sess_instance = AsyncMock()
            mock_tenant = MagicMock()
            mock_tenant.slug = "acme"
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_tenant
            mock_sess_instance.execute = AsyncMock(return_value=mock_result)
            MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_sess_instance)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await client.delete(
                f"/api/v1/tenants/{TENANT_ID}/trunks/{TRUNK_ID}"
            )
            assert resp.status_code == 200

    async def test_not_found_returns_404(self, client):
        with patch("new_phone.routers.sip_trunks.SIPTrunkService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_trunk = AsyncMock(return_value=_make_trunk())
            mock_svc.deactivate_trunk = AsyncMock(
                side_effect=ValueError("Trunk not found")
            )

            resp = await client.delete(
                f"/api/v1/tenants/{TENANT_ID}/trunks/{TRUNK_ID}"
            )
            assert resp.status_code == 404


# ── POST provision ──────────────────────────────────────────────────────


class TestProvisionTrunk:
    async def test_success_returns_201(self, client):
        with patch("new_phone.routers.sip_trunks.SIPTrunkService") as MockSvc, \
             patch("new_phone.routers.sip_trunks._sync_gateway_create", new_callable=AsyncMock):
            mock_svc = MockSvc.return_value
            mock_svc.provision = AsyncMock(return_value=_make_trunk())

            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/trunks/provision",
                json={
                    "provider": "clearlyip",
                    "name": "New Trunk",
                    "region": "us-east",
                    "channels": 30,
                },
            )
            assert resp.status_code == 201

    async def test_bad_request_returns_400(self, client):
        with patch("new_phone.routers.sip_trunks.SIPTrunkService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.provision = AsyncMock(
                side_effect=ValueError("Invalid region")
            )

            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/trunks/provision",
                json={
                    "provider": "clearlyip",
                    "name": "New Trunk",
                    "region": "invalid",
                    "channels": 30,
                },
            )
            assert resp.status_code == 400


# ── POST deprovision ───────────────────────────────────────────────────


class TestDeprovisionTrunk:
    async def test_success_returns_200(self, client):
        with patch("new_phone.routers.sip_trunks.SIPTrunkService") as MockSvc, \
             patch("new_phone.routers.sip_trunks._sync_gateway_change", new_callable=AsyncMock), \
             patch("new_phone.db.engine.AdminSessionLocal") as MockSession:
            trunk = _make_trunk(is_active=False)
            mock_svc = MockSvc.return_value
            mock_svc.deprovision = AsyncMock(return_value=trunk)
            # Mock the AdminSessionLocal context manager
            mock_sess_instance = AsyncMock()
            mock_tenant = MagicMock()
            mock_tenant.slug = "acme"
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_tenant
            mock_sess_instance.execute = AsyncMock(return_value=mock_result)
            MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_sess_instance)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/trunks/{TRUNK_ID}/deprovision"
            )
            assert resp.status_code == 200

    async def test_bad_request_returns_400(self, client):
        with patch("new_phone.routers.sip_trunks.SIPTrunkService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.deprovision = AsyncMock(
                side_effect=ValueError("Trunk not provisioned")
            )

            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/trunks/{TRUNK_ID}/deprovision"
            )
            assert resp.status_code == 400


# ── POST test ───────────────────────────────────────────────────────────


class TestTestTrunk:
    async def test_success_returns_200(self, client):
        test_result = MagicMock()
        test_result.status = "pass"
        test_result.latency_ms = 42.5
        test_result.error = None

        with patch("new_phone.routers.sip_trunks.SIPTrunkService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.test_trunk = AsyncMock(return_value=test_result)

            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/trunks/{TRUNK_ID}/test"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "pass"

    async def test_not_found_returns_404(self, client):
        with patch("new_phone.routers.sip_trunks.SIPTrunkService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.test_trunk = AsyncMock(
                side_effect=ValueError("Trunk not found")
            )

            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/trunks/{TRUNK_ID}/test"
            )
            assert resp.status_code == 404
