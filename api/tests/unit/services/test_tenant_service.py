"""Tests for new_phone.services.tenant_service — tenant CRUD."""

import uuid

import pytest

from new_phone.schemas.tenant import TenantCreate, TenantUpdate
from new_phone.services.tenant_service import TenantService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result, make_tenant


class TestListTenants:
    async def test_returns_list(self, mock_db):
        t1 = make_tenant(name="Acme", slug="acme")
        t2 = make_tenant(name="Globex", slug="globex")
        mock_db.execute.return_value = make_scalars_result([t1, t2])

        service = TenantService(mock_db)
        result = await service.list_tenants()
        assert len(result) == 2
        assert result[0].name == "Acme"

    async def test_returns_empty_list(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = TenantService(mock_db)
        result = await service.list_tenants()
        assert result == []


class TestGetTenant:
    async def test_found(self, mock_db):
        tenant = make_tenant(id=TENANT_ACME_ID, name="Acme")
        mock_db.execute.return_value = make_scalar_result(tenant)

        service = TenantService(mock_db)
        result = await service.get_tenant(TENANT_ACME_ID)
        assert result.name == "Acme"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TenantService(mock_db)
        result = await service.get_tenant(uuid.uuid4())
        assert result is None


class TestGetTenantBySlug:
    async def test_found(self, mock_db):
        tenant = make_tenant(slug="acme")
        mock_db.execute.return_value = make_scalar_result(tenant)
        service = TenantService(mock_db)
        result = await service.get_tenant_by_slug("acme")
        assert result.slug == "acme"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TenantService(mock_db)
        result = await service.get_tenant_by_slug("nonexistent")
        assert result is None


class TestCreateTenant:
    async def test_success(self, mock_db):
        # First call: slug check (not found), second: unused
        mock_db.execute.return_value = make_scalar_result(None)

        service = TenantService(mock_db)
        data = TenantCreate(name="New Co", slug="new-co")
        await service.create_tenant(data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_slug_raises(self, mock_db):
        existing = make_tenant(slug="acme")
        mock_db.execute.return_value = make_scalar_result(existing)

        service = TenantService(mock_db)
        data = TenantCreate(name="Acme 2", slug="acme")
        with pytest.raises(ValueError, match="already exists"):
            await service.create_tenant(data)

    async def test_auto_generates_sip_domain(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TenantService(mock_db)
        data = TenantCreate(name="AutoSIP", slug="auto-sip")
        await service.create_tenant(data)
        # The tenant object added to DB should have sip_domain set
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.sip_domain == "auto-sip.sip.local"


class TestUpdateTenant:
    async def test_success(self, mock_db):
        tenant = make_tenant(id=TENANT_ACME_ID, name="Old Name")
        mock_db.execute.return_value = make_scalar_result(tenant)

        service = TenantService(mock_db)
        data = TenantUpdate(name="New Name")
        await service.update_tenant(TENANT_ACME_ID, data)
        assert tenant.name == "New Name"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TenantService(mock_db)
        data = TenantUpdate(name="X")
        with pytest.raises(ValueError, match="not found"):
            await service.update_tenant(uuid.uuid4(), data)


class TestDeactivateTenant:
    async def test_success(self, mock_db):
        tenant = make_tenant(id=TENANT_ACME_ID, is_active=True)
        mock_db.execute.return_value = make_scalar_result(tenant)

        service = TenantService(mock_db)
        await service.deactivate_tenant(TENANT_ACME_ID)
        assert tenant.is_active is False
        assert tenant.deactivated_at is not None
