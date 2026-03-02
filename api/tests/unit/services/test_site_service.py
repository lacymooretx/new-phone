"""Tests for new_phone.services.site_service — site CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.site_service import SiteService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_site(**overrides):
    site = MagicMock()
    site.id = overrides.get("id", uuid.uuid4())
    site.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    site.name = overrides.get("name", "Main Office")
    site.timezone = overrides.get("timezone", "America/New_York")
    site.is_active = overrides.get("is_active", True)
    return site


class TestListSites:
    async def test_returns_list(self, mock_db):
        s1 = _make_site(name="Main Office")
        s2 = _make_site(name="Branch Office")
        mock_db.execute.return_value = make_scalars_result([s1, s2])

        service = SiteService(mock_db)
        result = await service.list_sites(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = SiteService(mock_db)
        result = await service.list_sites(TENANT_ACME_ID)
        assert result == []


class TestGetSite:
    async def test_found(self, mock_db):
        site = _make_site(name="Main Office")
        mock_db.execute.return_value = make_scalar_result(site)
        service = SiteService(mock_db)
        result = await service.get_site(TENANT_ACME_ID, site.id)
        assert result.name == "Main Office"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SiteService(mock_db)
        result = await service.get_site(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateSite:
    async def test_success(self, mock_db):
        from new_phone.schemas.site import SiteCreate

        mock_db.execute.return_value = make_scalar_result(None)  # no duplicate

        service = SiteService(mock_db)
        data = SiteCreate(name="New Site", timezone="America/Chicago")
        await service.create_site(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_name_raises(self, mock_db):
        from new_phone.schemas.site import SiteCreate

        existing = _make_site(name="Main Office")
        mock_db.execute.return_value = make_scalar_result(existing)

        service = SiteService(mock_db)
        data = SiteCreate(name="Main Office", timezone="America/New_York")
        with pytest.raises(ValueError, match="already exists"):
            await service.create_site(TENANT_ACME_ID, data)

    async def test_invalid_timezone_raises(self, mock_db):
        from new_phone.schemas.site import SiteCreate

        service = SiteService(mock_db)
        data = SiteCreate(name="Bad TZ Site", timezone="Not/A/Timezone")
        with pytest.raises(ValueError, match="Invalid timezone"):
            await service.create_site(TENANT_ACME_ID, data)


class TestUpdateSite:
    async def test_success(self, mock_db):
        from new_phone.schemas.site import SiteUpdate

        site = _make_site()
        mock_db.execute.side_effect = [
            make_scalar_result(site),  # get_site
            make_scalar_result(None),  # name uniqueness check
        ]
        service = SiteService(mock_db)
        data = SiteUpdate(name="Updated Office")
        await service.update_site(TENANT_ACME_ID, site.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.site import SiteUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = SiteService(mock_db)
        data = SiteUpdate(name="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_site(TENANT_ACME_ID, uuid.uuid4(), data)

    async def test_invalid_timezone_on_update_raises(self, mock_db):
        from new_phone.schemas.site import SiteUpdate

        site = _make_site()
        mock_db.execute.return_value = make_scalar_result(site)
        service = SiteService(mock_db)
        data = SiteUpdate(timezone="Fake/Zone")
        with pytest.raises(ValueError, match="Invalid timezone"):
            await service.update_site(TENANT_ACME_ID, site.id, data)


class TestDeactivateSite:
    async def test_success(self, mock_db):
        site = _make_site(is_active=True)
        mock_db.execute.return_value = make_scalar_result(site)
        service = SiteService(mock_db)
        await service.deactivate(TENANT_ACME_ID, site.id)
        assert site.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SiteService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate(TENANT_ACME_ID, uuid.uuid4())
