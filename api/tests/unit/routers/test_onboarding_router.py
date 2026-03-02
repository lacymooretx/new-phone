"""Tests for new_phone.routers.onboarding — tenant onboarding + status."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from new_phone.deps.auth import get_admin_db, get_current_user
from new_phone.models.user import UserRole
from new_phone.routers import onboarding
from tests.unit.conftest import TENANT_ACME_ID, make_user

TENANT_ID = TENANT_ACME_ID
NOW = datetime(2024, 1, 1, tzinfo=UTC)


def _mock_tenant(**overrides):
    defaults = dict(
        id=TENANT_ID,
        name="Acme Corp",
        slug="acme-corp",
        lifecycle_state="active",
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    t = MagicMock()
    for k, v in defaults.items():
        setattr(t, k, v)
    return t


@pytest.fixture
def app(mock_db, msp_admin_user):
    test_app = FastAPI()
    test_app.include_router(onboarding.router, prefix="/api/v1")

    async def override_db():
        yield mock_db

    test_app.dependency_overrides[get_admin_db] = override_db
    test_app.dependency_overrides[get_current_user] = lambda: msp_admin_user
    yield test_app
    test_app.dependency_overrides.clear()


# ── POST /onboarding/tenant ────────────────────────────────────────────


class TestOnboardTenant:
    async def test_success_returns_201(self, app, client):
        tenant = _mock_tenant()
        result = {
            "tenant": tenant,
            "trunk_provisioned": True,
            "dids_purchased": 2,
            "extensions_created": 10,
        }
        with patch("new_phone.routers.onboarding.TenantService") as MockSvc:
            MockSvc.return_value.onboard_tenant = AsyncMock(return_value=result)
            resp = await client.post(
                "/api/v1/onboarding/tenant",
                json={
                    "name": "Acme Corp",
                    "slug": "acme-corp",
                    "admin_email": "admin@acme.com",
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["tenant_name"] == "Acme Corp"
        assert data["trunk_provisioned"] is True
        assert data["dids_purchased"] == 2
        assert data["extensions_created"] == 10

    async def test_duplicate_slug_returns_409(self, app, client):
        with patch("new_phone.routers.onboarding.TenantService") as MockSvc:
            MockSvc.return_value.onboard_tenant = AsyncMock(
                side_effect=ValueError("Slug already exists")
            )
            resp = await client.post(
                "/api/v1/onboarding/tenant",
                json={
                    "name": "Acme Corp",
                    "slug": "acme-corp",
                    "admin_email": "admin@acme.com",
                },
            )
        assert resp.status_code == 409

    async def test_internal_error_returns_500(self, app, client):
        with patch("new_phone.routers.onboarding.TenantService") as MockSvc:
            MockSvc.return_value.onboard_tenant = AsyncMock(
                side_effect=RuntimeError("Provider unavailable")
            )
            resp = await client.post(
                "/api/v1/onboarding/tenant",
                json={
                    "name": "Acme Corp",
                    "slug": "acme-corp",
                    "admin_email": "admin@acme.com",
                },
            )
        assert resp.status_code == 500

    async def test_non_msp_returns_403(self, app, client):
        user = make_user(role=UserRole.TENANT_ADMIN)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = await client.post(
            "/api/v1/onboarding/tenant",
            json={
                "name": "Acme Corp",
                "slug": "acme-corp",
                "admin_email": "admin@acme.com",
            },
        )
        assert resp.status_code == 403


# ── GET /onboarding/status/{tenant_id} ─────────────────────────────────


class TestOnboardingStatus:
    async def test_success_returns_200(self, app, client, mock_db):
        tenant = _mock_tenant()
        trunk = MagicMock()
        trunk.name = "Primary Trunk"
        trunk.is_active = True
        did = MagicMock()
        did.is_active = True
        admin_user = MagicMock()
        admin_user.email = "admin@acme.com"
        admin_user.is_active = True
        ext = MagicMock()
        ext.is_active = True

        # The onboarding_status endpoint does raw db.execute() calls,
        # so we need to mock the return values in order.
        scalar_results = [tenant, trunk, None, admin_user, None]
        scalars_results = [[did], [ext]]
        scalar_idx = [0]
        scalars_idx = [0]

        def make_mock_result():
            """Build a mock result that can handle both scalar and scalars calls."""
            r = MagicMock()
            r.scalar_one_or_none.side_effect = lambda: _pop_scalar()
            scalars_mock = MagicMock()
            scalars_mock.all.side_effect = lambda: _pop_scalars()
            r.scalars.return_value = scalars_mock
            return r

        def _pop_scalar():
            idx = scalar_idx[0]
            scalar_idx[0] += 1
            if idx < len(scalar_results):
                return scalar_results[idx]
            return None

        def _pop_scalars():
            idx = scalars_idx[0]
            scalars_idx[0] += 1
            if idx < len(scalars_results):
                return scalars_results[idx]
            return []

        mock_db.execute = AsyncMock(side_effect=lambda *a, **kw: make_mock_result())

        resp = await client.get(f"/api/v1/onboarding/status/{TENANT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_name"] == "Acme Corp"
        assert isinstance(data["steps"], list)

    async def test_tenant_not_found_returns_404(self, app, client, mock_db):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        resp = await client.get(f"/api/v1/onboarding/status/{uuid.uuid4()}")
        assert resp.status_code == 404
