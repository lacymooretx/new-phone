"""Tests for new_phone.services.device_service — device CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.device_service import DeviceService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result


def _make_device(**overrides):
    device = MagicMock()
    device.id = overrides.get("id", uuid.uuid4())
    device.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    device.mac_address = overrides.get("mac_address", "001122334455")
    device.name = overrides.get("name", "Lobby Phone")
    device.phone_model_id = overrides.get("phone_model_id", uuid.uuid4())
    device.is_active = overrides.get("is_active", True)
    device.deactivated_at = overrides.get("deactivated_at")
    return device


class TestListDevices:
    async def test_returns_list(self, mock_db):
        d1 = _make_device(name="Lobby Phone")
        d2 = _make_device(name="Reception Phone")
        result_mock = MagicMock()
        unique_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [d1, d2]
        unique_mock.scalars.return_value = scalars_mock
        result_mock.unique.return_value = unique_mock
        mock_db.execute.return_value = result_mock

        service = DeviceService(mock_db)
        result = await service.list_devices(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        result_mock = MagicMock()
        unique_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        unique_mock.scalars.return_value = scalars_mock
        result_mock.unique.return_value = unique_mock
        mock_db.execute.return_value = result_mock

        service = DeviceService(mock_db)
        result = await service.list_devices(TENANT_ACME_ID)
        assert result == []


class TestGetDevice:
    async def test_found(self, mock_db):
        device = _make_device(name="Lobby Phone")
        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = device
        result_mock.unique.return_value = unique_mock
        mock_db.execute.return_value = result_mock

        service = DeviceService(mock_db)
        result = await service.get_device(TENANT_ACME_ID, device.id)
        assert result.name == "Lobby Phone"

    async def test_not_found(self, mock_db):
        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = None
        result_mock.unique.return_value = unique_mock
        mock_db.execute.return_value = result_mock

        service = DeviceService(mock_db)
        result = await service.get_device(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateDevice:
    async def test_success(self, mock_db):
        from new_phone.schemas.device import DeviceCreate

        mock_db.execute.return_value = make_scalar_result(None)  # no duplicate MAC

        service = DeviceService(mock_db)
        data = DeviceCreate(
            mac_address="AA:BB:CC:DD:EE:FF",
            phone_model_id=uuid.uuid4(),
        )
        await service.create_device(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_mac_raises(self, mock_db):
        from new_phone.schemas.device import DeviceCreate

        existing = _make_device(mac_address="aabbccddeeff")
        mock_db.execute.return_value = make_scalar_result(existing)

        service = DeviceService(mock_db)
        data = DeviceCreate(
            mac_address="AA:BB:CC:DD:EE:FF",
            phone_model_id=uuid.uuid4(),
        )
        with pytest.raises(ValueError, match="already registered"):
            await service.create_device(TENANT_ACME_ID, data)


class TestUpdateDevice:
    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.device import DeviceUpdate

        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = None
        result_mock.unique.return_value = unique_mock
        mock_db.execute.return_value = result_mock

        service = DeviceService(mock_db)
        data = DeviceUpdate(name="Updated")
        with pytest.raises(ValueError, match="not found"):
            await service.update_device(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateDevice:
    async def test_success(self, mock_db):
        device = _make_device(is_active=True)
        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = device
        result_mock.unique.return_value = unique_mock
        mock_db.execute.return_value = result_mock

        service = DeviceService(mock_db)
        await service.deactivate_device(TENANT_ACME_ID, device.id)
        assert device.is_active is False
        assert device.deactivated_at is not None

    async def test_not_found_raises(self, mock_db):
        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = None
        result_mock.unique.return_value = unique_mock
        mock_db.execute.return_value = result_mock

        service = DeviceService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_device(TENANT_ACME_ID, uuid.uuid4())
