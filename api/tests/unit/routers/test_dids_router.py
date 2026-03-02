"""Tests for new_phone.routers.dids — DID CRUD, search, purchase, release, routing."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from new_phone.deps.auth import get_admin_db, get_current_user
from new_phone.routers import dids

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DID_ID = uuid.UUID("00000000-0000-0000-0000-aaaaaaaaaaaa")


def _make_did(**overrides):
    from datetime import UTC, datetime

    defaults = dict(
        id=DID_ID,
        tenant_id=TENANT_ID,
        number="+15551234567",
        provider="clearlyip",
        provider_sid="ext-abc",
        status="active",
        is_emergency=False,
        sms_enabled=False,
        sms_queue_id=None,
        site_id=None,
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
    test_app.include_router(dids.router, prefix="/api/v1")

    async def override_db():
        yield mock_db

    test_app.dependency_overrides[get_admin_db] = override_db
    test_app.dependency_overrides[get_current_user] = lambda: acme_admin_user
    yield test_app
    test_app.dependency_overrides.clear()


# ── GET list ────────────────────────────────────────────────────────────


class TestListDids:
    async def test_success_returns_200(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.list_dids = AsyncMock(return_value=[_make_did()])

            resp = await client.get(f"/api/v1/tenants/{TENANT_ID}/dids")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) == 1

    async def test_empty_list_returns_200(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.list_dids = AsyncMock(return_value=[])

            resp = await client.get(f"/api/v1/tenants/{TENANT_ID}/dids")
            assert resp.status_code == 200
            assert resp.json() == []


# ── POST create ─────────────────────────────────────────────────────────


class TestCreateDid:
    async def test_success_returns_201(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc, \
             patch("new_phone.routers.dids._sync_dialplan", new_callable=AsyncMock):
            mock_svc = MockSvc.return_value
            mock_svc.create_did = AsyncMock(return_value=_make_did())

            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/dids",
                json={"number": "+15551234567", "provider": "clearlyip"},
            )
            assert resp.status_code == 201

    async def test_duplicate_returns_409(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.create_did = AsyncMock(
                side_effect=ValueError("DID already exists")
            )

            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/dids",
                json={"number": "+15551234567", "provider": "clearlyip"},
            )
            assert resp.status_code == 409
            assert "already exists" in resp.json()["detail"]


# ── GET detail ──────────────────────────────────────────────────────────


class TestGetDid:
    async def test_found_returns_200(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_did = AsyncMock(return_value=_make_did())

            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/dids/{DID_ID}"
            )
            assert resp.status_code == 200

    async def test_not_found_returns_404(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_did = AsyncMock(return_value=None)

            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/dids/{DID_ID}"
            )
            assert resp.status_code == 404


# ── PATCH update ────────────────────────────────────────────────────────


class TestUpdateDid:
    async def test_success_returns_200(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc, \
             patch("new_phone.routers.dids._sync_dialplan", new_callable=AsyncMock):
            mock_svc = MockSvc.return_value
            mock_svc.update_did = AsyncMock(return_value=_make_did())

            resp = await client.patch(
                f"/api/v1/tenants/{TENANT_ID}/dids/{DID_ID}",
                json={"e911_enabled": True},
            )
            assert resp.status_code == 200

    async def test_not_found_returns_404(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.update_did = AsyncMock(
                side_effect=ValueError("DID not found")
            )

            resp = await client.patch(
                f"/api/v1/tenants/{TENANT_ID}/dids/{DID_ID}",
                json={"e911_enabled": True},
            )
            assert resp.status_code == 404


# ── DELETE deactivate ───────────────────────────────────────────────────


class TestDeactivateDid:
    async def test_success_returns_200(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc, \
             patch("new_phone.routers.dids._sync_dialplan", new_callable=AsyncMock):
            mock_svc = MockSvc.return_value
            mock_svc.deactivate_did = AsyncMock(return_value=_make_did(is_active=False))

            resp = await client.delete(
                f"/api/v1/tenants/{TENANT_ID}/dids/{DID_ID}"
            )
            assert resp.status_code == 200

    async def test_not_found_returns_404(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.deactivate_did = AsyncMock(
                side_effect=ValueError("DID not found")
            )

            resp = await client.delete(
                f"/api/v1/tenants/{TENANT_ID}/dids/{DID_ID}"
            )
            assert resp.status_code == 404


# ── GET search ──────────────────────────────────────────────────────────


class TestSearchDids:
    async def test_search_returns_results(self, client):
        """GET /dids/search hits the search endpoint (not /{did_id})."""
        mock_result = MagicMock(
            number="+15559990000",
            monthly_cost=1.50,
            setup_cost=0.0,
            provider="clearlyip",
            capabilities={"voice": True, "sms": True},
        )
        with patch("new_phone.routers.dids.DIDService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.search_available = AsyncMock(return_value=[mock_result])

            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/dids/search",
                params={"area_code": "555"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["number"] == "+15559990000"


# ── POST purchase ───────────────────────────────────────────────────────


class TestPurchaseDid:
    async def test_success_returns_201(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc, \
             patch("new_phone.routers.dids._sync_dialplan", new_callable=AsyncMock):
            mock_svc = MockSvc.return_value
            mock_svc.purchase = AsyncMock(return_value=_make_did())

            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/dids/purchase",
                json={"number": "+15551234567", "provider": "clearlyip"},
            )
            assert resp.status_code == 201

    async def test_duplicate_returns_409(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.purchase = AsyncMock(
                side_effect=ValueError("DID already purchased")
            )

            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/dids/purchase",
                json={"number": "+15551234567", "provider": "clearlyip"},
            )
            assert resp.status_code == 409


# ── POST release ────────────────────────────────────────────────────────


class TestReleaseDid:
    async def test_success_returns_200(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc, \
             patch("new_phone.routers.dids._sync_dialplan", new_callable=AsyncMock):
            mock_svc = MockSvc.return_value
            mock_svc.release = AsyncMock(return_value=_make_did(is_active=False))

            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/dids/{DID_ID}/release"
            )
            assert resp.status_code == 200

    async def test_bad_request_returns_400(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.release = AsyncMock(
                side_effect=ValueError("Cannot release active DID")
            )

            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/dids/{DID_ID}/release"
            )
            assert resp.status_code == 400


# ── PUT routing ─────────────────────────────────────────────────────────


class TestConfigureRouting:
    async def test_success_returns_200(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc, \
             patch("new_phone.routers.dids._sync_dialplan", new_callable=AsyncMock):
            mock_svc = MockSvc.return_value
            mock_svc.configure_routing = AsyncMock(return_value=_make_did())

            dest_id = str(uuid.uuid4())
            resp = await client.put(
                f"/api/v1/tenants/{TENANT_ID}/dids/{DID_ID}/routing",
                json={"destination_type": "extension", "destination_id": dest_id},
            )
            assert resp.status_code == 200

    async def test_bad_request_returns_400(self, client):
        with patch("new_phone.routers.dids.DIDService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.configure_routing = AsyncMock(
                side_effect=ValueError("Invalid destination")
            )

            dest_id = str(uuid.uuid4())
            resp = await client.put(
                f"/api/v1/tenants/{TENANT_ID}/dids/{DID_ID}/routing",
                json={"destination_type": "extension", "destination_id": dest_id},
            )
            assert resp.status_code == 400
