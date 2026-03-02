"""Tests for new_phone.routers.tenants — tenant CRUD + permissions."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from new_phone.deps.auth import get_admin_db, get_current_user
from new_phone.models.user import UserRole
from new_phone.routers import tenants
from tests.unit.conftest import TENANT_ACME_ID, TENANT_GLOBEX_ID, make_tenant, make_user


@pytest.fixture
def app(mock_db, acme_admin_user):
    test_app = FastAPI()
    test_app.include_router(tenants.router, prefix="/api/v1")

    async def override_db():
        yield mock_db

    test_app.dependency_overrides[get_admin_db] = override_db
    test_app.dependency_overrides[get_current_user] = lambda: acme_admin_user
    yield test_app
    test_app.dependency_overrides.clear()


class TestListTenants:
    async def test_happy_path(self, app, client):
        # list_tenants requires VIEW_ALL_TENANTS — only MSP roles have it
        user = make_user(role=UserRole.MSP_SUPER_ADMIN)
        app.dependency_overrides[get_current_user] = lambda: user
        t1 = make_tenant(id=TENANT_ACME_ID, name="Acme", slug="acme")
        with patch("new_phone.routers.tenants.TenantService") as MockSvc:
            MockSvc.return_value.list_tenants = AsyncMock(return_value=[t1])
            resp = await client.get("/api/v1/tenants")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Acme"

    async def test_403_for_tenant_user(self, app, client):
        user = make_user(role=UserRole.TENANT_USER)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = await client.get("/api/v1/tenants")
        assert resp.status_code == 403

    async def test_403_for_tenant_manager(self, app, client):
        user = make_user(role=UserRole.TENANT_MANAGER)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = await client.get("/api/v1/tenants")
        assert resp.status_code == 403

    async def test_allowed_for_msp_tech(self, app, client):
        user = make_user(role=UserRole.MSP_TECH)
        app.dependency_overrides[get_current_user] = lambda: user
        with patch("new_phone.routers.tenants.TenantService") as MockSvc:
            MockSvc.return_value.list_tenants = AsyncMock(return_value=[])
            resp = await client.get("/api/v1/tenants")
        assert resp.status_code == 200


class TestCreateTenant:
    async def test_success_201(self, app, client):
        user = make_user(role=UserRole.MSP_SUPER_ADMIN)
        app.dependency_overrides[get_current_user] = lambda: user
        new_tenant = make_tenant(name="New Co", slug="new-co")
        with patch("new_phone.routers.tenants.TenantService") as MockSvc:
            MockSvc.return_value.create_tenant = AsyncMock(return_value=new_tenant)
            resp = await client.post(
                "/api/v1/tenants",
                json={"name": "New Co", "slug": "new-co"},
            )
        assert resp.status_code == 201
        assert resp.json()["name"] == "New Co"

    async def test_duplicate_slug_409(self, app, client):
        user = make_user(role=UserRole.MSP_SUPER_ADMIN)
        app.dependency_overrides[get_current_user] = lambda: user
        with patch("new_phone.routers.tenants.TenantService") as MockSvc:
            MockSvc.return_value.create_tenant = AsyncMock(side_effect=ValueError("already exists"))
            resp = await client.post(
                "/api/v1/tenants",
                json={"name": "Acme", "slug": "acme"},
            )
        assert resp.status_code == 409

    async def test_403_for_tenant_admin(self, app, client):
        resp = await client.post(
            "/api/v1/tenants",
            json={"name": "X", "slug": "x"},
        )
        # Default user is tenant_admin who lacks MANAGE_PLATFORM
        assert resp.status_code == 403


class TestGetTenant:
    async def test_own_tenant(self, app, client):
        tenant = make_tenant(id=TENANT_ACME_ID, name="Acme", slug="acme")
        with patch("new_phone.routers.tenants.TenantService") as MockSvc:
            MockSvc.return_value.get_tenant = AsyncMock(return_value=tenant)
            resp = await client.get(f"/api/v1/tenants/{TENANT_ACME_ID}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Acme"

    async def test_cross_tenant_403(self, app, client):
        resp = await client.get(f"/api/v1/tenants/{TENANT_GLOBEX_ID}")
        assert resp.status_code == 403

    async def test_msp_can_view_any(self, app, client):
        user = make_user(role=UserRole.MSP_SUPER_ADMIN)
        app.dependency_overrides[get_current_user] = lambda: user
        tenant = make_tenant(id=TENANT_GLOBEX_ID, name="Globex", slug="globex")
        with patch("new_phone.routers.tenants.TenantService") as MockSvc:
            MockSvc.return_value.get_tenant = AsyncMock(return_value=tenant)
            resp = await client.get(f"/api/v1/tenants/{TENANT_GLOBEX_ID}")
        assert resp.status_code == 200

    async def test_not_found_404(self, app, client):
        user = make_user(role=UserRole.MSP_SUPER_ADMIN)
        app.dependency_overrides[get_current_user] = lambda: user
        with patch("new_phone.routers.tenants.TenantService") as MockSvc:
            MockSvc.return_value.get_tenant = AsyncMock(return_value=None)
            resp = await client.get(f"/api/v1/tenants/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestUpdateTenant:
    async def test_success(self, app, client):
        tenant = make_tenant(id=TENANT_ACME_ID, name="Updated")
        with patch("new_phone.routers.tenants.TenantService") as MockSvc:
            MockSvc.return_value.update_tenant = AsyncMock(return_value=tenant)
            resp = await client.patch(
                f"/api/v1/tenants/{TENANT_ACME_ID}",
                json={"name": "Updated"},
            )
        assert resp.status_code == 200

    async def test_cross_tenant_403(self, app, client):
        resp = await client.patch(
            f"/api/v1/tenants/{TENANT_GLOBEX_ID}",
            json={"name": "Hacked"},
        )
        assert resp.status_code == 403


class TestDeactivateTenant:
    async def test_success(self, app, client):
        user = make_user(role=UserRole.MSP_SUPER_ADMIN)
        app.dependency_overrides[get_current_user] = lambda: user
        tenant = make_tenant(id=TENANT_ACME_ID, is_active=False)
        with patch("new_phone.routers.tenants.TenantService") as MockSvc:
            MockSvc.return_value.deactivate_tenant = AsyncMock(return_value=tenant)
            resp = await client.delete(f"/api/v1/tenants/{TENANT_ACME_ID}")
        assert resp.status_code == 200

    async def test_403_for_tenant_admin(self, app, client):
        resp = await client.delete(f"/api/v1/tenants/{TENANT_ACME_ID}")
        assert resp.status_code == 403
