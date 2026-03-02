"""Tests for new_phone.services.tenant_service — tenant CRUD + lifecycle + onboarding."""

import uuid
from unittest.mock import AsyncMock

import pytest

from new_phone.schemas.tenant import TenantCreate, TenantUpdate
from new_phone.services.tenant_service import TenantService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result, make_tenant


class TestListTenants:
    async def test_returns_all(self, mock_db):
        t1 = make_tenant(name="Acme")
        t2 = make_tenant(name="Globex")
        mock_db.execute.return_value = make_scalars_result([t1, t2])

        service = TenantService(mock_db)
        result = await service.list_tenants()
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = TenantService(mock_db)
        result = await service.list_tenants()
        assert result == []


class TestGetTenant:
    async def test_found(self, mock_db):
        tenant = make_tenant(id=TENANT_ACME_ID)
        mock_db.execute.return_value = make_scalar_result(tenant)
        service = TenantService(mock_db)
        result = await service.get_tenant(TENANT_ACME_ID)
        assert result is tenant

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TenantService(mock_db)
        result = await service.get_tenant(uuid.uuid4())
        assert result is None


class TestCreateTenant:
    async def test_success(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = TenantCreate(name="New Corp", slug="new-corp")

        service = TenantService(mock_db)
        await service.create_tenant(data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    async def test_auto_generates_sip_domain(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = TenantCreate(name="Test Corp", slug="test-corp")

        service = TenantService(mock_db)
        await service.create_tenant(data)
        added = mock_db.add.call_args[0][0]
        assert added.sip_domain == "test-corp.sip.local"

    async def test_duplicate_slug_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(make_tenant(slug="dup"))
        data = TenantCreate(name="Dup Corp", slug="dup")

        service = TenantService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_tenant(data)


class TestUpdateTenant:
    async def test_success(self, mock_db):
        tenant = make_tenant(id=TENANT_ACME_ID, name="Old Name")
        mock_db.execute.return_value = make_scalar_result(tenant)
        data = TenantUpdate(name="New Name")

        service = TenantService(mock_db)
        await service.update_tenant(TENANT_ACME_ID, data)
        assert tenant.name == "New Name"
        mock_db.commit.assert_awaited_once()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TenantService(mock_db)
        with pytest.raises(ValueError, match="Tenant not found"):
            await service.update_tenant(uuid.uuid4(), TenantUpdate(name="X"))


class TestDeactivateTenant:
    async def test_success(self, mock_db):
        tenant = make_tenant(id=TENANT_ACME_ID)
        mock_db.execute.return_value = make_scalar_result(tenant)

        service = TenantService(mock_db)
        await service.deactivate_tenant(TENANT_ACME_ID)
        assert tenant.is_active is False
        assert tenant.lifecycle_state == "cancelled"
        assert tenant.deactivated_at is not None

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TenantService(mock_db)
        with pytest.raises(ValueError, match="Tenant not found"):
            await service.deactivate_tenant(uuid.uuid4())


class TestSetLifecycleState:
    async def test_set_to_active(self, mock_db):
        tenant = make_tenant(id=TENANT_ACME_ID, is_active=False)
        mock_db.execute.return_value = make_scalar_result(tenant)

        service = TenantService(mock_db)
        await service.set_lifecycle_state(TENANT_ACME_ID, "active")
        assert tenant.lifecycle_state == "active"
        assert tenant.is_active is True
        assert tenant.deactivated_at is None

    async def test_set_to_cancelled(self, mock_db):
        tenant = make_tenant(id=TENANT_ACME_ID)
        mock_db.execute.return_value = make_scalar_result(tenant)

        service = TenantService(mock_db)
        await service.set_lifecycle_state(TENANT_ACME_ID, "cancelled")
        assert tenant.is_active is False
        assert tenant.deactivated_at is not None

    async def test_set_to_suspended(self, mock_db):
        tenant = make_tenant(id=TENANT_ACME_ID)
        mock_db.execute.return_value = make_scalar_result(tenant)

        service = TenantService(mock_db)
        await service.set_lifecycle_state(TENANT_ACME_ID, "suspended")
        assert tenant.lifecycle_state == "suspended"

    async def test_invalid_state_raises(self, mock_db):
        service = TenantService(mock_db)
        with pytest.raises(ValueError, match="Invalid lifecycle state"):
            await service.set_lifecycle_state(TENANT_ACME_ID, "bogus")

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TenantService(mock_db)
        with pytest.raises(ValueError, match="Tenant not found"):
            await service.set_lifecycle_state(uuid.uuid4(), "active")


class TestOnboardTenant:
    async def test_basic_onboard_no_dids_no_extensions(self, mock_db):
        """Onboard with 0 DIDs and 0 extensions — only tenant + admin created."""
        # get_tenant_by_slug returns None (no dup), admin user check returns None
        mock_db.execute.return_value = make_scalar_result(None)
        mock_db.flush = AsyncMock()

        service = TenantService(mock_db)
        result = await service.onboard_tenant(
            name="Test Corp",
            slug="test-corp",
            domain=None,
            admin_email="admin@test.com",
            plan="trial",
            initial_did_count=0,
            initial_extensions=0,
        )
        assert "tenant" in result
        assert "steps" in result
        assert isinstance(result["steps"], list)
        # trunk provisioning will fail (no real provider) but should not crash
        mock_db.commit.assert_awaited()

    async def test_duplicate_slug_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(make_tenant(slug="dup"))
        service = TenantService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.onboard_tenant(
                name="Dup",
                slug="dup",
                domain=None,
                admin_email="a@b.com",
            )
