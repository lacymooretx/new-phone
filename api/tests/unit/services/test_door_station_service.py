"""Tests for new_phone.services.door_station_service — door station CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.door_station_service import DoorStationService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_door_station(**overrides):
    ds = MagicMock()
    ds.id = overrides.get("id", uuid.uuid4())
    ds.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    ds.extension_id = overrides.get("extension_id", uuid.uuid4())
    ds.name = overrides.get("name", "Main Entrance")
    ds.unlock_url = overrides.get("unlock_url", "http://192.168.1.100/unlock")
    ds.unlock_http_method = overrides.get("unlock_http_method", "POST")
    ds.unlock_headers = overrides.get("unlock_headers")
    ds.unlock_body = overrides.get("unlock_body")
    ds.is_active = overrides.get("is_active", True)
    return ds


def _make_extension(**overrides):
    ext = MagicMock()
    ext.id = overrides.get("id", uuid.uuid4())
    ext.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    ext.extension_number = overrides.get("extension_number", "100")
    return ext


class TestListDoorStations:
    async def test_returns_list(self, mock_db):
        d1 = _make_door_station(name="Main Entrance")
        d2 = _make_door_station(name="Side Door")
        mock_db.execute.return_value = make_scalars_result([d1, d2])

        service = DoorStationService(mock_db)
        result = await service.list_door_stations(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = DoorStationService(mock_db)
        result = await service.list_door_stations(TENANT_ACME_ID)
        assert result == []


class TestGetDoorStation:
    async def test_found(self, mock_db):
        ds = _make_door_station(name="Main Entrance")
        mock_db.execute.return_value = make_scalar_result(ds)
        service = DoorStationService(mock_db)
        result = await service.get_door_station(TENANT_ACME_ID, ds.id)
        assert result.name == "Main Entrance"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = DoorStationService(mock_db)
        result = await service.get_door_station(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateDoorStation:
    async def test_success(self, mock_db):
        from new_phone.schemas.door_station import DoorStationCreate

        ext_id = uuid.uuid4()
        ext = _make_extension(id=ext_id)
        mock_db.execute.return_value = make_scalar_result(ext)

        service = DoorStationService(mock_db)
        data = DoorStationCreate(
            extension_id=ext_id,
            name="New Door Station",
            unlock_url="http://192.168.1.200/unlock",
        )
        await service.create_door_station(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_extension_not_found_raises(self, mock_db):
        from new_phone.schemas.door_station import DoorStationCreate

        mock_db.execute.return_value = make_scalar_result(None)

        service = DoorStationService(mock_db)
        data = DoorStationCreate(
            extension_id=uuid.uuid4(),
            name="Bad Door Station",
        )
        with pytest.raises(ValueError, match="Extension not found"):
            await service.create_door_station(TENANT_ACME_ID, data)


class TestUpdateDoorStation:
    async def test_success(self, mock_db):
        from new_phone.schemas.door_station import DoorStationUpdate

        ds = _make_door_station()
        mock_db.execute.return_value = make_scalar_result(ds)
        service = DoorStationService(mock_db)
        data = DoorStationUpdate(name="Updated Station")
        await service.update_door_station(TENANT_ACME_ID, ds.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.door_station import DoorStationUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = DoorStationService(mock_db)
        data = DoorStationUpdate(name="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_door_station(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateDoorStation:
    async def test_success(self, mock_db):
        ds = _make_door_station(is_active=True)
        mock_db.execute.return_value = make_scalar_result(ds)
        service = DoorStationService(mock_db)
        await service.deactivate_door_station(TENANT_ACME_ID, ds.id)
        assert ds.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = DoorStationService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_door_station(TENANT_ACME_ID, uuid.uuid4())
