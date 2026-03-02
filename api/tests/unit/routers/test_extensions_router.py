"""Tests for new_phone.routers.extensions — extension CRUD + permissions."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from new_phone.deps.auth import get_admin_db, get_current_user
from new_phone.models.user import UserRole
from new_phone.routers import extensions
from tests.unit.conftest import TENANT_ACME_ID, TENANT_GLOBEX_ID, make_user


@pytest.fixture
def app(mock_db, acme_admin_user):
    test_app = FastAPI()
    test_app.include_router(extensions.router, prefix="/api/v1")

    async def override_db():
        yield mock_db

    test_app.dependency_overrides[get_admin_db] = override_db
    test_app.dependency_overrides[get_current_user] = lambda: acme_admin_user
    yield test_app
    test_app.dependency_overrides.clear()


def _mock_ext(**overrides):
    ext = MagicMock()
    ext.id = overrides.get("id", uuid.uuid4())
    ext.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    ext.extension_number = overrides.get("extension_number", "100")
    ext.sip_username = overrides.get("sip_username", "00000000-100")
    ext.user_id = overrides.get("user_id")
    ext.voicemail_box_id = overrides.get("voicemail_box_id")
    ext.internal_cid_name = overrides.get("internal_cid_name")
    ext.internal_cid_number = overrides.get("internal_cid_number")
    ext.external_cid_name = overrides.get("external_cid_name")
    ext.external_cid_number = overrides.get("external_cid_number")
    ext.emergency_cid_number = overrides.get("emergency_cid_number")
    ext.e911_street = overrides.get("e911_street")
    ext.e911_city = overrides.get("e911_city")
    ext.e911_state = overrides.get("e911_state")
    ext.e911_zip = overrides.get("e911_zip")
    ext.e911_country = overrides.get("e911_country")
    ext.call_forward_unconditional = None
    ext.call_forward_busy = None
    ext.call_forward_no_answer = None
    ext.call_forward_not_registered = None
    ext.call_forward_ring_time = 25
    ext.dnd_enabled = False
    ext.call_waiting = True
    ext.max_registrations = 3
    ext.outbound_cid_mode = "internal"
    ext.class_of_service = "domestic"
    ext.recording_policy = "never"
    ext.notes = None
    ext.agent_status = None
    ext.pickup_group = None
    ext.site_id = None
    ext.is_active = True
    from datetime import UTC, datetime

    ext.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    ext.updated_at = datetime(2024, 1, 1, tzinfo=UTC)
    return ext


class TestListExtensions:
    async def test_happy_path(self, app, client):
        e1 = _mock_ext(extension_number="100")
        with patch("new_phone.routers.extensions.ExtensionService") as MockSvc:
            MockSvc.return_value.list_extensions = AsyncMock(return_value=[e1])
            resp = await client.get(f"/api/v1/tenants/{TENANT_ACME_ID}/extensions")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_cross_tenant_403(self, app, client):
        resp = await client.get(f"/api/v1/tenants/{TENANT_GLOBEX_ID}/extensions")
        assert resp.status_code == 403

    async def test_tenant_user_can_view(self, app, client):
        user = make_user(role=UserRole.TENANT_USER)
        app.dependency_overrides[get_current_user] = lambda: user
        with patch("new_phone.routers.extensions.ExtensionService") as MockSvc:
            MockSvc.return_value.list_extensions = AsyncMock(return_value=[])
            resp = await client.get(f"/api/v1/tenants/{TENANT_ACME_ID}/extensions")
        assert resp.status_code == 200


class TestCreateExtension:
    async def test_success_201(self, app, client):
        ext = _mock_ext(extension_number="200")
        with (
            patch("new_phone.routers.extensions.ExtensionService") as MockSvc,
            patch("new_phone.routers.extensions.log_audit", new_callable=AsyncMock),
            patch("new_phone.routers.extensions._sync_directory", new_callable=AsyncMock),
        ):
            MockSvc.return_value.create_extension = AsyncMock(return_value=ext)
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ACME_ID}/extensions",
                json={"extension_number": "200"},
            )
        assert resp.status_code == 201

    async def test_duplicate_409(self, app, client):
        with (
            patch("new_phone.routers.extensions.ExtensionService") as MockSvc,
            patch("new_phone.routers.extensions.log_audit", new_callable=AsyncMock),
        ):
            MockSvc.return_value.create_extension = AsyncMock(
                side_effect=ValueError("already exists")
            )
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ACME_ID}/extensions",
                json={"extension_number": "100"},
            )
        assert resp.status_code == 409

    async def test_tenant_user_cannot_create(self, app, client):
        user = make_user(role=UserRole.TENANT_USER)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = await client.post(
            f"/api/v1/tenants/{TENANT_ACME_ID}/extensions",
            json={"extension_number": "200"},
        )
        assert resp.status_code == 403


class TestGetExtension:
    async def test_found(self, app, client):
        ext_id = uuid.uuid4()
        ext = _mock_ext(id=ext_id)
        with patch("new_phone.routers.extensions.ExtensionService") as MockSvc:
            MockSvc.return_value.get_extension = AsyncMock(return_value=ext)
            resp = await client.get(f"/api/v1/tenants/{TENANT_ACME_ID}/extensions/{ext_id}")
        assert resp.status_code == 200

    async def test_not_found_404(self, app, client):
        with patch("new_phone.routers.extensions.ExtensionService") as MockSvc:
            MockSvc.return_value.get_extension = AsyncMock(return_value=None)
            resp = await client.get(f"/api/v1/tenants/{TENANT_ACME_ID}/extensions/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestUpdateExtension:
    async def test_success(self, app, client):
        ext_id = uuid.uuid4()
        ext = _mock_ext(id=ext_id)
        with (
            patch("new_phone.routers.extensions.ExtensionService") as MockSvc,
            patch("new_phone.routers.extensions.log_audit", new_callable=AsyncMock),
            patch("new_phone.routers.extensions._sync_directory", new_callable=AsyncMock),
        ):
            MockSvc.return_value.update_extension = AsyncMock(return_value=ext)
            resp = await client.patch(
                f"/api/v1/tenants/{TENANT_ACME_ID}/extensions/{ext_id}",
                json={"notes": "updated"},
            )
        assert resp.status_code == 200

    async def test_not_found_404(self, app, client):
        with (
            patch("new_phone.routers.extensions.ExtensionService") as MockSvc,
            patch("new_phone.routers.extensions.log_audit", new_callable=AsyncMock),
        ):
            MockSvc.return_value.update_extension = AsyncMock(side_effect=ValueError("not found"))
            resp = await client.patch(
                f"/api/v1/tenants/{TENANT_ACME_ID}/extensions/{uuid.uuid4()}",
                json={"notes": "x"},
            )
        assert resp.status_code == 404


class TestDeactivateExtension:
    async def test_success(self, app, client):
        ext_id = uuid.uuid4()
        ext = _mock_ext(id=ext_id, is_active=False)
        with (
            patch("new_phone.routers.extensions.ExtensionService") as MockSvc,
            patch("new_phone.routers.extensions.log_audit", new_callable=AsyncMock),
            patch("new_phone.routers.extensions._sync_directory", new_callable=AsyncMock),
        ):
            MockSvc.return_value.deactivate_extension = AsyncMock(return_value=ext)
            resp = await client.delete(f"/api/v1/tenants/{TENANT_ACME_ID}/extensions/{ext_id}")
        assert resp.status_code == 200

    async def test_tenant_user_cannot_delete(self, app, client):
        user = make_user(role=UserRole.TENANT_USER)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = await client.delete(f"/api/v1/tenants/{TENANT_ACME_ID}/extensions/{uuid.uuid4()}")
        assert resp.status_code == 403


class TestResetSipPassword:
    async def test_success(self, app, client):
        ext_id = uuid.uuid4()
        with (
            patch("new_phone.routers.extensions.ExtensionService") as MockSvc,
            patch("new_phone.routers.extensions._sync_directory", new_callable=AsyncMock),
        ):
            MockSvc.return_value.reset_sip_password = AsyncMock(return_value="newpassword123abc")
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ACME_ID}/extensions/{ext_id}/reset-sip-password"
            )
        assert resp.status_code == 200
        assert resp.json()["sip_password"] == "newpassword123abc"
