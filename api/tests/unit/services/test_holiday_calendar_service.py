"""Tests for new_phone.services.holiday_calendar_service — holiday calendar CRUD."""

import uuid
from datetime import date
from unittest.mock import MagicMock

import pytest

from new_phone.services.holiday_calendar_service import HolidayCalendarService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_calendar(**overrides):
    cal = MagicMock()
    cal.id = overrides.get("id", uuid.uuid4())
    cal.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    cal.name = overrides.get("name", "US Holidays")
    cal.description = overrides.get("description", "Federal holidays")
    cal.is_active = overrides.get("is_active", True)
    cal.entries = overrides.get("entries", [])
    return cal


class TestListCalendars:
    async def test_returns_list(self, mock_db):
        c1 = _make_calendar(name="US Holidays")
        c2 = _make_calendar(name="UK Holidays")
        mock_db.execute.return_value = make_scalars_result([c1, c2])

        service = HolidayCalendarService(mock_db)
        result = await service.list_calendars(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = HolidayCalendarService(mock_db)
        result = await service.list_calendars(TENANT_ACME_ID)
        assert result == []


class TestGetCalendar:
    async def test_found(self, mock_db):
        cal = _make_calendar(name="US Holidays")
        mock_db.execute.return_value = make_scalar_result(cal)
        service = HolidayCalendarService(mock_db)
        result = await service.get_calendar(TENANT_ACME_ID, cal.id)
        assert result.name == "US Holidays"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = HolidayCalendarService(mock_db)
        result = await service.get_calendar(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateCalendar:
    async def test_success(self, mock_db):
        from new_phone.schemas.holiday_calendar import HolidayCalendarCreate, HolidayEntryData

        mock_db.execute.return_value = make_scalar_result(None)  # no duplicate

        service = HolidayCalendarService(mock_db)
        data = HolidayCalendarCreate(
            name="New Calendar",
            entries=[
                HolidayEntryData(name="New Year", date=date(2025, 1, 1), recur_annually=True),
            ],
        )
        await service.create_calendar(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_name_raises(self, mock_db):
        from new_phone.schemas.holiday_calendar import HolidayCalendarCreate

        existing = _make_calendar(name="US Holidays")
        mock_db.execute.return_value = make_scalar_result(existing)

        service = HolidayCalendarService(mock_db)
        data = HolidayCalendarCreate(name="US Holidays")
        with pytest.raises(ValueError, match="already exists"):
            await service.create_calendar(TENANT_ACME_ID, data)


class TestUpdateCalendar:
    async def test_success(self, mock_db):
        from new_phone.schemas.holiday_calendar import HolidayCalendarUpdate

        cal = _make_calendar()
        mock_db.execute.return_value = make_scalar_result(cal)
        service = HolidayCalendarService(mock_db)
        data = HolidayCalendarUpdate(name="Updated Calendar")
        await service.update_calendar(TENANT_ACME_ID, cal.id, data)
        assert cal.name == "Updated Calendar"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.holiday_calendar import HolidayCalendarUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = HolidayCalendarService(mock_db)
        data = HolidayCalendarUpdate(name="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_calendar(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateCalendar:
    async def test_success(self, mock_db):
        cal = _make_calendar(is_active=True)
        mock_db.execute.return_value = make_scalar_result(cal)
        service = HolidayCalendarService(mock_db)
        await service.deactivate(TENANT_ACME_ID, cal.id)
        assert cal.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = HolidayCalendarService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate(TENANT_ACME_ID, uuid.uuid4())
