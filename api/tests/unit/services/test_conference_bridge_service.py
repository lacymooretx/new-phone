"""Tests for new_phone.services.conference_bridge_service — conference bridge CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.conference_bridge_service import ConferenceBridgeService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_bridge(**overrides):
    bridge = MagicMock()
    bridge.id = overrides.get("id", uuid.uuid4())
    bridge.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    bridge.name = overrides.get("name", "All Hands")
    bridge.room_number = overrides.get("room_number", "800")
    bridge.is_active = overrides.get("is_active", True)
    bridge.deactivated_at = overrides.get("deactivated_at")
    return bridge


class TestListBridges:
    async def test_returns_list(self, mock_db):
        b1 = _make_bridge(name="All Hands")
        b2 = _make_bridge(name="Standup")
        mock_db.execute.return_value = make_scalars_result([b1, b2])

        service = ConferenceBridgeService(mock_db)
        result = await service.list_bridges(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = ConferenceBridgeService(mock_db)
        result = await service.list_bridges(TENANT_ACME_ID)
        assert result == []


class TestGetBridge:
    async def test_found(self, mock_db):
        bridge = _make_bridge(name="All Hands")
        mock_db.execute.return_value = make_scalar_result(bridge)
        service = ConferenceBridgeService(mock_db)
        result = await service.get_bridge(TENANT_ACME_ID, bridge.id)
        assert result.name == "All Hands"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ConferenceBridgeService(mock_db)
        result = await service.get_bridge(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateBridge:
    async def test_success(self, mock_db):
        from new_phone.schemas.conference_bridge import ConferenceBridgeCreate

        # No duplicate name, no duplicate room_number
        mock_db.execute.side_effect = [
            make_scalar_result(None),  # name check
            make_scalar_result(None),  # room_number check
        ]
        service = ConferenceBridgeService(mock_db)
        data = ConferenceBridgeCreate(name="New Bridge", room_number="801")
        await service.create_bridge(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_name_raises(self, mock_db):
        from new_phone.schemas.conference_bridge import ConferenceBridgeCreate

        existing = _make_bridge(name="All Hands")
        mock_db.execute.return_value = make_scalar_result(existing)

        service = ConferenceBridgeService(mock_db)
        data = ConferenceBridgeCreate(name="All Hands", room_number="802")
        with pytest.raises(ValueError, match="already exists"):
            await service.create_bridge(TENANT_ACME_ID, data)

    async def test_duplicate_room_number_raises(self, mock_db):
        from new_phone.schemas.conference_bridge import ConferenceBridgeCreate

        mock_db.execute.side_effect = [
            make_scalar_result(None),  # name check passes
            make_scalar_result(_make_bridge(room_number="800")),  # room_number duplicate
        ]
        service = ConferenceBridgeService(mock_db)
        data = ConferenceBridgeCreate(name="Unique Name", room_number="800")
        with pytest.raises(ValueError, match="already exists"):
            await service.create_bridge(TENANT_ACME_ID, data)


class TestUpdateBridge:
    async def test_success(self, mock_db):
        from new_phone.schemas.conference_bridge import ConferenceBridgeUpdate

        bridge = _make_bridge()
        mock_db.execute.return_value = make_scalar_result(bridge)
        service = ConferenceBridgeService(mock_db)
        data = ConferenceBridgeUpdate(name="Updated Bridge")
        # The update will call get_bridge first, then the name uniqueness check
        mock_db.execute.side_effect = [
            make_scalar_result(bridge),  # get_bridge
            make_scalar_result(None),   # name uniqueness check
        ]
        await service.update_bridge(TENANT_ACME_ID, bridge.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.conference_bridge import ConferenceBridgeUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = ConferenceBridgeService(mock_db)
        data = ConferenceBridgeUpdate(name="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_bridge(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateBridge:
    async def test_success(self, mock_db):
        bridge = _make_bridge(is_active=True)
        mock_db.execute.return_value = make_scalar_result(bridge)
        service = ConferenceBridgeService(mock_db)
        await service.deactivate(TENANT_ACME_ID, bridge.id)
        assert bridge.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ConferenceBridgeService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate(TENANT_ACME_ID, uuid.uuid4())
