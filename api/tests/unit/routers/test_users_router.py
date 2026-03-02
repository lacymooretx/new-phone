"""Tests for new_phone.routers.users — user CRUD + permissions."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from new_phone.deps.auth import get_admin_db, get_current_user
from new_phone.models.user import UserRole
from new_phone.routers import users
from tests.unit.conftest import (
    TENANT_ACME_ID,
    TENANT_GLOBEX_ID,
    make_user,
)


@pytest.fixture
def app(mock_db, acme_admin_user):
    test_app = FastAPI()
    test_app.include_router(users.router, prefix="/api/v1")

    async def override_db():
        yield mock_db

    test_app.dependency_overrides[get_admin_db] = override_db
    test_app.dependency_overrides[get_current_user] = lambda: acme_admin_user
    yield test_app
    test_app.dependency_overrides.clear()


class TestListUsers:
    async def test_happy_path(self, app, client):
        u1 = make_user(email="alice@acme.com")
        with patch("new_phone.routers.users.UserService") as MockSvc:
            MockSvc.return_value.list_users = AsyncMock(return_value=[u1])
            resp = await client.get(f"/api/v1/tenants/{TENANT_ACME_ID}/users")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_cross_tenant_403(self, app, client):
        resp = await client.get(f"/api/v1/tenants/{TENANT_GLOBEX_ID}/users")
        assert resp.status_code == 403

    async def test_403_for_tenant_user(self, app, client):
        user = make_user(role=UserRole.TENANT_USER)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = await client.get(f"/api/v1/tenants/{TENANT_ACME_ID}/users")
        assert resp.status_code == 403

    async def test_msp_can_view_any_tenant(self, app, client):
        user = make_user(role=UserRole.MSP_SUPER_ADMIN)
        app.dependency_overrides[get_current_user] = lambda: user
        with patch("new_phone.routers.users.UserService") as MockSvc:
            MockSvc.return_value.list_users = AsyncMock(return_value=[])
            resp = await client.get(f"/api/v1/tenants/{TENANT_GLOBEX_ID}/users")
        assert resp.status_code == 200


class TestCreateUser:
    async def test_success_201(self, app, client):
        new_user = make_user(email="new@acme.com", first_name="New")
        with patch("new_phone.routers.users.UserService") as MockSvc:
            MockSvc.return_value.create_user = AsyncMock(return_value=new_user)
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ACME_ID}/users",
                json={
                    "email": "new@acme.com",
                    "password": "securepass1",
                    "first_name": "New",
                    "last_name": "User",
                },
            )
        assert resp.status_code == 201

    async def test_duplicate_email_409(self, app, client):
        with patch("new_phone.routers.users.UserService") as MockSvc:
            MockSvc.return_value.create_user = AsyncMock(side_effect=ValueError("already exists"))
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ACME_ID}/users",
                json={
                    "email": "taken@acme.com",
                    "password": "securepass1",
                    "first_name": "Dup",
                    "last_name": "User",
                },
            )
        assert resp.status_code == 409

    async def test_cross_tenant_403(self, app, client):
        resp = await client.post(
            f"/api/v1/tenants/{TENANT_GLOBEX_ID}/users",
            json={
                "email": "x@g.com",
                "password": "securepass1",
                "first_name": "X",
                "last_name": "Y",
            },
        )
        assert resp.status_code == 403


class TestGetUser:
    async def test_own_profile(self, app, client, acme_admin_user):
        with patch("new_phone.routers.users.UserService") as MockSvc:
            MockSvc.return_value.get_user = AsyncMock(return_value=acme_admin_user)
            resp = await client.get(f"/api/v1/tenants/{TENANT_ACME_ID}/users/{acme_admin_user.id}")
        assert resp.status_code == 200

    async def test_not_found_404(self, app, client):
        missing_id = uuid.uuid4()
        with patch("new_phone.routers.users.UserService") as MockSvc:
            MockSvc.return_value.get_user = AsyncMock(return_value=None)
            resp = await client.get(f"/api/v1/tenants/{TENANT_ACME_ID}/users/{missing_id}")
        assert resp.status_code == 404

    async def test_tenant_user_cannot_view_others(self, app, client):
        viewer = make_user(role=UserRole.TENANT_USER)
        app.dependency_overrides[get_current_user] = lambda: viewer
        other_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/tenants/{TENANT_ACME_ID}/users/{other_id}")
        assert resp.status_code == 403


class TestUpdateUser:
    async def test_success(self, app, client, acme_admin_user):
        updated = make_user(id=acme_admin_user.id, first_name="Updated")
        with patch("new_phone.routers.users.UserService") as MockSvc:
            MockSvc.return_value.update_user = AsyncMock(return_value=updated)
            resp = await client.patch(
                f"/api/v1/tenants/{TENANT_ACME_ID}/users/{acme_admin_user.id}",
                json={"first_name": "Updated"},
            )
        assert resp.status_code == 200


class TestDeactivateUser:
    async def test_success(self, app, client):
        user_id = uuid.uuid4()
        deactivated = make_user(id=user_id, is_active=False)
        with patch("new_phone.routers.users.UserService") as MockSvc:
            MockSvc.return_value.deactivate_user = AsyncMock(return_value=deactivated)
            resp = await client.delete(f"/api/v1/tenants/{TENANT_ACME_ID}/users/{user_id}")
        assert resp.status_code == 200

    async def test_403_for_tenant_user(self, app, client):
        user = make_user(role=UserRole.TENANT_USER)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = await client.delete(f"/api/v1/tenants/{TENANT_ACME_ID}/users/{uuid.uuid4()}")
        assert resp.status_code == 403
