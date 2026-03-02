"""Tests for new_phone.services.ring_group_service — ring group CRUD + members."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from new_phone.schemas.ring_group import RingGroupCreate, RingGroupUpdate
from new_phone.services.ring_group_service import RingGroupService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_ring_group(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        group_number="600",
        name="Sales Ring Group",
        ring_strategy="simultaneous",
        ring_time=25,
        ring_time_per_member=15,
        skip_busy=True,
        cid_passthrough=True,
        confirm_calls=False,
        failover_dest_type=None,
        failover_dest_id=None,
        moh_prompt_id=None,
        is_active=True,
        deactivated_at=None,
        members=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListRingGroups:
    async def test_returns_groups(self, mock_db):
        g1 = _make_ring_group(name="Sales")
        g2 = _make_ring_group(name="Support")
        mock_db.execute.return_value = make_scalars_result([g1, g2])

        service = RingGroupService(mock_db)
        result = await service.list_ring_groups(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = RingGroupService(mock_db)
        result = await service.list_ring_groups(TENANT_ACME_ID)
        assert result == []


class TestGetRingGroup:
    async def test_found(self, mock_db):
        group = _make_ring_group()
        mock_db.execute.return_value = make_scalar_result(group)
        service = RingGroupService(mock_db)
        result = await service.get_ring_group(TENANT_ACME_ID, group.id)
        assert result is group

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = RingGroupService(mock_db)
        result = await service.get_ring_group(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateRingGroup:
    async def test_success_with_members(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)  # no duplicate
        ext_ids = [uuid.uuid4(), uuid.uuid4()]
        data = RingGroupCreate(
            group_number="601",
            name="New RG",
            member_extension_ids=ext_ids,
        )

        service = RingGroupService(mock_db)
        await service.create_ring_group(TENANT_ACME_ID, data)
        # 1 group + 2 members = 3 add calls
        assert mock_db.add.call_count == 3
        mock_db.flush.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    async def test_duplicate_group_number_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(_make_ring_group())
        data = RingGroupCreate(group_number="600", name="Dup RG")

        service = RingGroupService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_ring_group(TENANT_ACME_ID, data)


class TestUpdateRingGroup:
    async def test_success(self, mock_db):
        group = _make_ring_group()
        mock_db.execute.return_value = make_scalar_result(group)
        data = RingGroupUpdate(name="Updated RG")

        service = RingGroupService(mock_db)
        await service.update_ring_group(TENANT_ACME_ID, group.id, data)
        assert group.name == "Updated RG"
        mock_db.commit.assert_awaited_once()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = RingGroupService(mock_db)
        with pytest.raises(ValueError, match="Ring group not found"):
            await service.update_ring_group(
                TENANT_ACME_ID, uuid.uuid4(), RingGroupUpdate(name="X")
            )

    async def test_replaces_members(self, mock_db):
        group = _make_ring_group()
        mock_db.execute.side_effect = [
            make_scalar_result(group),  # get_ring_group
            MagicMock(rowcount=2),      # delete old members
        ]
        new_ext_ids = [uuid.uuid4()]
        data = RingGroupUpdate(member_extension_ids=new_ext_ids)

        service = RingGroupService(mock_db)
        await service.update_ring_group(TENANT_ACME_ID, group.id, data)
        mock_db.commit.assert_awaited_once()


class TestDeactivateRingGroup:
    async def test_success(self, mock_db):
        group = _make_ring_group()
        mock_db.execute.return_value = make_scalar_result(group)

        service = RingGroupService(mock_db)
        await service.deactivate_ring_group(TENANT_ACME_ID, group.id)
        assert group.is_active is False
        assert group.deactivated_at is not None

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = RingGroupService(mock_db)
        with pytest.raises(ValueError, match="Ring group not found"):
            await service.deactivate_ring_group(TENANT_ACME_ID, uuid.uuid4())
