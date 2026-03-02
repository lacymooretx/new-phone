"""Tests for new_phone.services.ring_group_service — ring group CRUD + members."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.ring_group_service import RingGroupService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_ring_group(**overrides):
    rg = MagicMock()
    rg.id = overrides.get("id", uuid.uuid4())
    rg.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    rg.group_number = overrides.get("group_number", "600")
    rg.name = overrides.get("name", "Sales Group")
    rg.is_active = overrides.get("is_active", True)
    rg.deactivated_at = overrides.get("deactivated_at")
    return rg


class TestListRingGroups:
    async def test_returns_list(self, mock_db):
        r1 = _make_ring_group(name="Sales")
        r2 = _make_ring_group(name="Support")
        mock_db.execute.return_value = make_scalars_result([r1, r2])

        service = RingGroupService(mock_db)
        result = await service.list_ring_groups(TENANT_ACME_ID)
        assert len(result) == 2


class TestGetRingGroup:
    async def test_found(self, mock_db):
        rg = _make_ring_group(name="Sales")
        mock_db.execute.return_value = make_scalar_result(rg)
        service = RingGroupService(mock_db)
        result = await service.get_ring_group(TENANT_ACME_ID, rg.id)
        assert result.name == "Sales"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = RingGroupService(mock_db)
        result = await service.get_ring_group(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateRingGroup:
    async def test_success(self, mock_db):
        from new_phone.schemas.ring_group import RingGroupCreate

        mock_db.execute.return_value = make_scalar_result(None)  # no duplicate

        service = RingGroupService(mock_db)
        ext_id = uuid.uuid4()
        data = RingGroupCreate(
            group_number="601",
            name="New Group",
            ring_time=25,
            member_extension_ids=[ext_id],
        )
        await service.create_ring_group(TENANT_ACME_ID, data)
        # ring group + 1 member = 2 add calls
        assert mock_db.add.call_count == 2

    async def test_duplicate_number_raises(self, mock_db):
        from new_phone.schemas.ring_group import RingGroupCreate

        existing = _make_ring_group(group_number="600")
        mock_db.execute.return_value = make_scalar_result(existing)

        service = RingGroupService(mock_db)
        data = RingGroupCreate(
            group_number="600",
            name="Another",
            ring_time=25,
            member_extension_ids=[],
        )
        with pytest.raises(ValueError, match="already exists"):
            await service.create_ring_group(TENANT_ACME_ID, data)


class TestUpdateRingGroup:
    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.ring_group import RingGroupUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = RingGroupService(mock_db)
        data = RingGroupUpdate(name="X")
        with pytest.raises(ValueError, match="not found"):
            await service.update_ring_group(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateRingGroup:
    async def test_success(self, mock_db):
        rg = _make_ring_group(is_active=True)
        mock_db.execute.return_value = make_scalar_result(rg)
        service = RingGroupService(mock_db)
        await service.deactivate_ring_group(TENANT_ACME_ID, rg.id)
        assert rg.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = RingGroupService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_ring_group(TENANT_ACME_ID, uuid.uuid4())
