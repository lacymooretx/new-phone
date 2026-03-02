"""Tests for new_phone.services.wfm_service — WFM shifts, schedules, time-off CRUD."""

import uuid
from datetime import date, time
from unittest.mock import MagicMock, patch

import pytest

from new_phone.services.wfm_service import WfmService
from tests.unit.conftest import (
    TENANT_ACME_ID,
    USER_ACME_ADMIN_ID,
    make_scalar_result,
    make_scalars_result,
)


def _make_shift(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        name="Morning",
        start_time=time(8, 0),
        end_time=time(16, 0),
        break_minutes=30,
        color="#00FF00",
        is_active=True,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_schedule_entry(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        extension_id=uuid.uuid4(),
        shift_id=uuid.uuid4(),
        date=date(2024, 1, 15),
        notes=None,
        shift=None,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_time_off(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        extension_id=uuid.uuid4(),
        start_date=date(2024, 1, 20),
        end_date=date(2024, 1, 22),
        reason="Vacation",
        status="pending",
        reviewed_by_id=None,
        reviewed_at=None,
        review_notes=None,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListShifts:
    async def test_returns_list(self, mock_db):
        s1 = _make_shift(name="Morning")
        s2 = _make_shift(name="Evening")
        mock_db.execute.return_value = make_scalars_result([s1, s2])

        service = WfmService(mock_db)
        result = await service.list_shifts(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_returns_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = WfmService(mock_db)
        result = await service.list_shifts(TENANT_ACME_ID)
        assert result == []


class TestGetShift:
    async def test_found(self, mock_db):
        shift = _make_shift()
        mock_db.execute.return_value = make_scalar_result(shift)

        service = WfmService(mock_db)
        result = await service.get_shift(TENANT_ACME_ID, shift.id)
        assert result.name == "Morning"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = WfmService(mock_db)
        result = await service.get_shift(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateShift:
    async def test_success(self, mock_db):
        # Duplicate check returns None
        mock_db.execute.return_value = make_scalar_result(None)

        data = MagicMock()
        data.name = "Night"
        data.start_time = time(22, 0)
        data.end_time = time(6, 0)
        data.break_minutes = 30
        data.color = "#FF0000"

        service = WfmService(mock_db)
        await service.create_shift(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_name_raises(self, mock_db):
        existing = _make_shift(name="Morning")
        mock_db.execute.return_value = make_scalar_result(existing)

        data = MagicMock()
        data.name = "Morning"

        service = WfmService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_shift(TENANT_ACME_ID, data)


class TestUpdateShift:
    async def test_success(self, mock_db):
        shift = _make_shift(name="Old")
        # set_tenant_context execute, get_shift execute, name duplicate check execute
        mock_db.execute.side_effect = [
            MagicMock(),  # set_tenant_context
            make_scalar_result(shift),
            make_scalar_result(None),
        ]

        data = MagicMock()
        data.model_dump.return_value = {"name": "Updated"}

        service = WfmService(mock_db)
        result = await service.update_shift(TENANT_ACME_ID, shift.id, data)
        assert result.name == "Updated"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = MagicMock()
        data.model_dump.return_value = {}

        service = WfmService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.update_shift(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateShift:
    async def test_success(self, mock_db):
        shift = _make_shift(is_active=True)
        mock_db.execute.return_value = make_scalar_result(shift)

        service = WfmService(mock_db)
        result = await service.deactivate_shift(TENANT_ACME_ID, shift.id)
        assert result.is_active is False
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = WfmService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_shift(TENANT_ACME_ID, uuid.uuid4())


class TestCreateTimeOffRequest:
    async def test_success(self, mock_db):
        data = MagicMock()
        data.extension_id = uuid.uuid4()
        data.start_date = date(2024, 2, 1)
        data.end_date = date(2024, 2, 3)
        data.reason = "Personal"

        service = WfmService(mock_db)
        await service.create_time_off_request(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_end_before_start_raises(self, mock_db):
        data = MagicMock()
        data.start_date = date(2024, 2, 5)
        data.end_date = date(2024, 2, 1)

        service = WfmService(mock_db)
        with pytest.raises(ValueError, match="End date"):
            await service.create_time_off_request(TENANT_ACME_ID, data)


class TestReviewTimeOffRequest:
    async def test_approve_success(self, mock_db):
        req = _make_time_off(status="pending")
        mock_db.execute.return_value = make_scalar_result(req)

        review = MagicMock()
        review.status = "approved"
        review.review_notes = "Approved"

        service = WfmService(mock_db)
        with patch("new_phone.services.wfm_service.WfmTimeOffStatus") as mock_status:
            mock_status.PENDING = "pending"
            result = await service.review_time_off_request(
                TENANT_ACME_ID, req.id, USER_ACME_ADMIN_ID, review
            )

        assert result.status == "approved"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        review = MagicMock()

        service = WfmService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.review_time_off_request(
                TENANT_ACME_ID, uuid.uuid4(), USER_ACME_ADMIN_ID, review
            )

    async def test_already_reviewed_raises(self, mock_db):
        req = _make_time_off(status="approved")
        mock_db.execute.return_value = make_scalar_result(req)

        review = MagicMock()
        service = WfmService(mock_db)
        with patch("new_phone.services.wfm_service.WfmTimeOffStatus") as mock_status:
            mock_status.PENDING = "pending"
            with pytest.raises(ValueError, match="already"):
                await service.review_time_off_request(
                    TENANT_ACME_ID, req.id, USER_ACME_ADMIN_ID, review
                )


class TestDeleteScheduleEntry:
    async def test_success(self, mock_db):
        entry = _make_schedule_entry()
        mock_db.execute.return_value = make_scalar_result(entry)

        service = WfmService(mock_db)
        await service.delete_schedule_entry(TENANT_ACME_ID, entry.id)
        mock_db.delete.assert_awaited()
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = WfmService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.delete_schedule_entry(TENANT_ACME_ID, uuid.uuid4())
