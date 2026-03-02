"""Tests for new_phone.services.parking_service — parking lot CRUD + slot overlap."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from new_phone.schemas.parking_lot import ParkingLotCreate, ParkingLotUpdate
from new_phone.services.parking_service import ParkingService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_lot(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        name="Main Lot",
        lot_number=1,
        slot_start=701,
        slot_end=710,
        timeout_seconds=60,
        comeback_enabled=True,
        comeback_extension=None,
        moh_prompt_id=None,
        site_id=None,
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListLots:
    async def test_returns_lots(self, mock_db):
        l1 = _make_lot(name="Lot A")
        l2 = _make_lot(name="Lot B")
        mock_db.execute.return_value = make_scalars_result([l1, l2])

        service = ParkingService(mock_db)
        result = await service.list_lots(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = ParkingService(mock_db)
        result = await service.list_lots(TENANT_ACME_ID)
        assert result == []

    async def test_filters_by_site(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([_make_lot()])
        service = ParkingService(mock_db)
        result = await service.list_lots(TENANT_ACME_ID, site_id=uuid.uuid4())
        assert len(result) == 1


class TestGetLot:
    async def test_found(self, mock_db):
        lot = _make_lot()
        mock_db.execute.return_value = make_scalar_result(lot)
        service = ParkingService(mock_db)
        result = await service.get_lot(TENANT_ACME_ID, lot.id)
        assert result is lot

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ParkingService(mock_db)
        result = await service.get_lot(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateLot:
    async def test_success(self, mock_db):
        # lot_number check, name check, list_lots for overlap
        mock_db.execute.side_effect = [
            make_scalar_result(None),    # lot_number unique
            make_scalar_result(None),    # name unique
            make_scalars_result([]),      # no existing lots (overlap check)
        ]
        data = ParkingLotCreate(name="New Lot", lot_number=2, slot_start=711, slot_end=720)

        service = ParkingService(mock_db)
        await service.create_lot(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    async def test_duplicate_lot_number_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(_make_lot())
        data = ParkingLotCreate(name="Dup", lot_number=1, slot_start=801, slot_end=810)

        service = ParkingService(mock_db)
        with pytest.raises(ValueError, match=r"lot number.*already exists"):
            await service.create_lot(TENANT_ACME_ID, data)

    async def test_duplicate_name_raises(self, mock_db):
        mock_db.execute.side_effect = [
            make_scalar_result(None),           # lot_number ok
            make_scalar_result(_make_lot()),     # name duplicate
        ]
        data = ParkingLotCreate(name="Main Lot", lot_number=99, slot_start=801, slot_end=810)

        service = ParkingService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_lot(TENANT_ACME_ID, data)

    async def test_overlapping_slots_raises(self, mock_db):
        existing_lot = _make_lot(slot_start=701, slot_end=710)
        mock_db.execute.side_effect = [
            make_scalar_result(None),               # lot_number ok
            make_scalar_result(None),               # name ok
            make_scalars_result([existing_lot]),     # overlap check
        ]
        data = ParkingLotCreate(name="Overlap", lot_number=3, slot_start=705, slot_end=715)

        service = ParkingService(mock_db)
        with pytest.raises(ValueError, match="overlaps"):
            await service.create_lot(TENANT_ACME_ID, data)


class TestUpdateLot:
    async def test_success(self, mock_db):
        lot = _make_lot()
        mock_db.execute.return_value = make_scalar_result(lot)
        data = ParkingLotUpdate(timeout_seconds=120)

        service = ParkingService(mock_db)
        await service.update_lot(TENANT_ACME_ID, lot.id, data)
        assert lot.timeout_seconds == 120
        mock_db.commit.assert_awaited_once()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ParkingService(mock_db)
        with pytest.raises(ValueError, match="Parking lot not found"):
            await service.update_lot(
                TENANT_ACME_ID, uuid.uuid4(), ParkingLotUpdate(name="X")
            )


class TestDeactivateLot:
    async def test_success(self, mock_db):
        lot = _make_lot()
        mock_db.execute.return_value = make_scalar_result(lot)

        service = ParkingService(mock_db)
        await service.deactivate(TENANT_ACME_ID, lot.id)
        assert lot.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ParkingService(mock_db)
        with pytest.raises(ValueError, match="Parking lot not found"):
            await service.deactivate(TENANT_ACME_ID, uuid.uuid4())
