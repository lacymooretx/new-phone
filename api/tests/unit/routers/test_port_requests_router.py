"""Tests for new_phone.routers.port_requests — port request lifecycle."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from new_phone.deps.auth import get_admin_db, get_current_user
from new_phone.routers import port_requests
from tests.unit.conftest import TENANT_ACME_ID

TENANT_ID = TENANT_ACME_ID
PORT_ID = uuid.UUID("00000000-0000-0000-0000-ffffffffffff")
NOW = datetime(2024, 1, 1, tzinfo=UTC)


def _mock_port_request(**overrides):
    defaults = dict(
        id=PORT_ID,
        tenant_id=TENANT_ID,
        numbers=["+15551112222"],
        current_carrier="OldTelco",
        status="submitted",
        provider="clearlyip",
        provider_port_id=None,
        loa_file_path=None,
        foc_date=None,
        requested_port_date=None,
        actual_port_date=None,
        rejection_reason=None,
        notes=None,
        submitted_by=uuid.uuid4(),
        created_at=NOW,
        updated_at=NOW,
        history=[],
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


@pytest.fixture
def app(mock_db, acme_admin_user):
    test_app = FastAPI()
    test_app.include_router(port_requests.router, prefix="/api/v1")

    async def override_db():
        yield mock_db

    test_app.dependency_overrides[get_admin_db] = override_db
    test_app.dependency_overrides[get_current_user] = lambda: acme_admin_user
    yield test_app
    test_app.dependency_overrides.clear()


# ── POST create ─────────────────────────────────────────────────────────


class TestCreatePortRequest:
    async def test_success_returns_201(self, app, client):
        with patch("new_phone.routers.port_requests.PortService") as MockSvc:
            MockSvc.return_value.submit_port_request = AsyncMock(
                return_value=_mock_port_request()
            )
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/port-requests",
                json={
                    "numbers": ["+15551112222"],
                    "current_carrier": "OldTelco",
                    "provider": "clearlyip",
                },
            )
        assert resp.status_code == 201
        assert resp.json()["status"] == "submitted"

    async def test_bad_request_returns_400(self, app, client):
        with patch("new_phone.routers.port_requests.PortService") as MockSvc:
            MockSvc.return_value.submit_port_request = AsyncMock(
                side_effect=ValueError("Invalid phone number format")
            )
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/port-requests",
                json={
                    "numbers": ["+15551112222"],
                    "current_carrier": "OldTelco",
                    "provider": "clearlyip",
                },
            )
        assert resp.status_code == 400


# ── GET list ────────────────────────────────────────────────────────────


class TestListPortRequests:
    async def test_success_returns_200(self, app, client):
        with patch("new_phone.routers.port_requests.PortService") as MockSvc:
            MockSvc.return_value.list_port_requests = AsyncMock(
                return_value=[_mock_port_request()]
            )
            resp = await client.get(f"/api/v1/tenants/{TENANT_ID}/port-requests")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 1

    async def test_empty_list_returns_200(self, app, client):
        with patch("new_phone.routers.port_requests.PortService") as MockSvc:
            MockSvc.return_value.list_port_requests = AsyncMock(return_value=[])
            resp = await client.get(f"/api/v1/tenants/{TENANT_ID}/port-requests")
        assert resp.status_code == 200
        assert resp.json() == []


# ── GET detail ──────────────────────────────────────────────────────────


class TestGetPortRequest:
    async def test_found_returns_200(self, app, client):
        with patch("new_phone.routers.port_requests.PortService") as MockSvc:
            MockSvc.return_value.get_port_request = AsyncMock(
                return_value=_mock_port_request()
            )
            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/port-requests/{PORT_ID}"
            )
        assert resp.status_code == 200

    async def test_not_found_returns_404(self, app, client):
        with patch("new_phone.routers.port_requests.PortService") as MockSvc:
            MockSvc.return_value.get_port_request = AsyncMock(return_value=None)
            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/port-requests/{PORT_ID}"
            )
        assert resp.status_code == 404


# ── POST upload-loa ─────────────────────────────────────────────────────


class TestUploadLoa:
    async def test_success_returns_200(self, app, client):
        with patch("new_phone.routers.port_requests.PortService") as MockSvc, \
             patch("new_phone.main.storage_service") as mock_storage:
            mock_storage.client = MagicMock()
            mock_storage.upload_bytes = MagicMock(return_value=True)
            MockSvc.return_value.upload_loa = AsyncMock(
                return_value=_mock_port_request(
                    loa_file_path="port-requests/tenant/port/loa.pdf"
                )
            )
            # Multipart file upload
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/port-requests/{PORT_ID}/upload-loa",
                files={"file": ("loa.pdf", b"%PDF-1.4 fake content", "application/pdf")},
            )
        assert resp.status_code == 200

    async def test_storage_unavailable_returns_503(self, app, client):
        mock_storage = MagicMock()
        mock_storage.client = None
        with patch("new_phone.main.storage_service", mock_storage):
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/port-requests/{PORT_ID}/upload-loa",
                files={"file": ("loa.pdf", b"%PDF-1.4 fake content", "application/pdf")},
            )
        assert resp.status_code == 503


# ── POST check-status ──────────────────────────────────────────────────


class TestCheckPortStatus:
    async def test_success_returns_200(self, app, client):
        with patch("new_phone.routers.port_requests.PortService") as MockSvc:
            MockSvc.return_value.check_status = AsyncMock(
                return_value=_mock_port_request(status="foc_received")
            )
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/port-requests/{PORT_ID}/check-status"
            )
        assert resp.status_code == 200

    async def test_not_found_returns_404(self, app, client):
        with patch("new_phone.routers.port_requests.PortService") as MockSvc:
            MockSvc.return_value.check_status = AsyncMock(
                side_effect=ValueError("Port request not found")
            )
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/port-requests/{PORT_ID}/check-status"
            )
        assert resp.status_code == 404


# ── POST cancel ─────────────────────────────────────────────────────────


class TestCancelPortRequest:
    async def test_success_returns_200(self, app, client):
        with patch("new_phone.routers.port_requests.PortService") as MockSvc:
            MockSvc.return_value.cancel_port = AsyncMock(
                return_value=_mock_port_request(status="cancelled")
            )
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/port-requests/{PORT_ID}/cancel"
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    async def test_bad_request_returns_400(self, app, client):
        with patch("new_phone.routers.port_requests.PortService") as MockSvc:
            MockSvc.return_value.cancel_port = AsyncMock(
                side_effect=ValueError("Cannot cancel completed port")
            )
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/port-requests/{PORT_ID}/cancel"
            )
        assert resp.status_code == 400
