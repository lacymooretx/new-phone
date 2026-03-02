"""Tests for new_phone.services.paging_zone_service — paging zone CRUD."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from new_phone.services.paging_zone_service import PagingZoneService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_zone(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        name="Lobby Zone",
        zone_number="801",
        description="Lobby paging zone",
        is_emergency=False,
        is_active=True,
        priority=1,
        site_id=None,
        members=[],
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListZones:
    async def test_returns_list(self, mock_db):
        z1 = _make_zone(name="Lobby")
        z2 = _make_zone(name="Warehouse")
        mock_db.execute.return_value = make_scalars_result([z1, z2])

        service = PagingZoneService(mock_db)
        result = await service.list_zones(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_returns_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = PagingZoneService(mock_db)
        result = await service.list_zones(TENANT_ACME_ID)
        assert result == []


class TestGetZone:
    async def test_found(self, mock_db):
        zone = _make_zone()
        mock_db.execute.return_value = make_scalar_result(zone)

        service = PagingZoneService(mock_db)
        result = await service.get_zone(TENANT_ACME_ID, zone.id)
        assert result.name == "Lobby Zone"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = PagingZoneService(mock_db)
        result = await service.get_zone(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateZone:
    async def test_success(self, mock_db):
        data = MagicMock()
        data.name = "New Zone"
        data.zone_number = "802"
        data.description = "A new zone"
        data.is_emergency = False
        data.priority = 1
        data.site_id = None
        data.members = []

        # First execute: duplicate check (none found)
        mock_db.execute.return_value = make_scalar_result(None)

        service = PagingZoneService(mock_db)
        with patch("new_phone.services.paging_zone_service.set_tenant_context", new_callable=AsyncMock):
            await service.create_zone(TENANT_ACME_ID, data)

        mock_db.add.assert_called()
        mock_db.commit.assert_awaited()

    async def test_duplicate_zone_number_raises(self, mock_db):
        existing = _make_zone(zone_number="801")
        data = MagicMock()
        data.zone_number = "801"

        mock_db.execute.return_value = make_scalar_result(existing)

        service = PagingZoneService(mock_db)
        with (
            patch("new_phone.services.paging_zone_service.set_tenant_context", new_callable=AsyncMock),
            pytest.raises(ValueError, match="already exists"),
        ):
            await service.create_zone(TENANT_ACME_ID, data)


class TestUpdateZone:
    async def test_success(self, mock_db):
        zone = _make_zone(name="Old Name")
        mock_db.execute.return_value = make_scalar_result(zone)

        data = MagicMock()
        data.model_dump.return_value = {"name": "New Name"}
        data.members = None

        service = PagingZoneService(mock_db)
        result = await service.update_zone(TENANT_ACME_ID, zone.id, data)
        assert result.name == "New Name"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)

        data = MagicMock()
        data.model_dump.return_value = {}
        data.members = None

        service = PagingZoneService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.update_zone(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateZone:
    async def test_success(self, mock_db):
        zone = _make_zone(is_active=True)
        mock_db.execute.return_value = make_scalar_result(zone)

        service = PagingZoneService(mock_db)
        result = await service.deactivate_zone(TENANT_ACME_ID, zone.id)
        assert result.is_active is False
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = PagingZoneService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_zone(TENANT_ACME_ID, uuid.uuid4())
