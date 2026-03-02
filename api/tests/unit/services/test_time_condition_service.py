"""Tests for new_phone.services.time_condition_service — time condition CRUD."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from new_phone.schemas.time_condition import (
    TimeConditionCreate,
    TimeConditionRule,
    TimeConditionUpdate,
)
from new_phone.services.time_condition_service import TimeConditionService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_tc(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        name="Business Hours",
        description="Mon-Fri 8-5",
        timezone="America/New_York",
        rules=[{"type": "day_of_week", "days": [1, 2, 3, 4, 5]}],
        match_destination_type="ivr_menu",
        match_destination_id=uuid.uuid4(),
        nomatch_destination_type="voicemail",
        nomatch_destination_id=uuid.uuid4(),
        enabled=True,
        is_active=True,
        site_id=None,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListTimeConditions:
    async def test_returns_conditions(self, mock_db):
        tc1 = _make_tc(name="Business Hours")
        tc2 = _make_tc(name="After Hours")
        mock_db.execute.return_value = make_scalars_result([tc1, tc2])

        service = TimeConditionService(mock_db)
        result = await service.list_time_conditions(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = TimeConditionService(mock_db)
        result = await service.list_time_conditions(TENANT_ACME_ID)
        assert result == []

    async def test_filters_by_site(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([_make_tc()])
        service = TimeConditionService(mock_db)
        result = await service.list_time_conditions(TENANT_ACME_ID, site_id=uuid.uuid4())
        assert len(result) == 1


class TestGetTimeCondition:
    async def test_found(self, mock_db):
        tc = _make_tc()
        mock_db.execute.return_value = make_scalar_result(tc)
        service = TimeConditionService(mock_db)
        result = await service.get_time_condition(TENANT_ACME_ID, tc.id)
        assert result is tc

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TimeConditionService(mock_db)
        result = await service.get_time_condition(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateTimeCondition:
    async def test_success(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = TimeConditionCreate(
            name="New TC",
            match_destination_type="extension",
            nomatch_destination_type="voicemail",
            rules=[TimeConditionRule(type="day_of_week", days=[1, 2, 3])],
        )

        service = TimeConditionService(mock_db)
        await service.create_time_condition(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    async def test_duplicate_name_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(_make_tc())
        data = TimeConditionCreate(
            name="Business Hours",
            match_destination_type="extension",
            nomatch_destination_type="voicemail",
        )

        service = TimeConditionService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_time_condition(TENANT_ACME_ID, data)


class TestUpdateTimeCondition:
    async def test_success(self, mock_db):
        tc = _make_tc()
        mock_db.execute.return_value = make_scalar_result(tc)
        data = TimeConditionUpdate(description="Updated desc")

        service = TimeConditionService(mock_db)
        await service.update_time_condition(TENANT_ACME_ID, tc.id, data)
        assert tc.description == "Updated desc"
        mock_db.commit.assert_awaited_once()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TimeConditionService(mock_db)
        with pytest.raises(ValueError, match="Time condition not found"):
            await service.update_time_condition(
                TENANT_ACME_ID, uuid.uuid4(), TimeConditionUpdate(name="X")
            )


class TestDeactivateTimeCondition:
    async def test_success(self, mock_db):
        tc = _make_tc()
        mock_db.execute.return_value = make_scalar_result(tc)

        service = TimeConditionService(mock_db)
        await service.deactivate(TENANT_ACME_ID, tc.id)
        assert tc.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TimeConditionService(mock_db)
        with pytest.raises(ValueError, match="Time condition not found"):
            await service.deactivate(TENANT_ACME_ID, uuid.uuid4())
