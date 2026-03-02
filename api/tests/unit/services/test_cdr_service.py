"""Tests for new_phone.services.cdr_service — CDR listing, filtering, disposition."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from new_phone.schemas.cdr import CDRFilter
from new_phone.services.cdr_service import CDRService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_cdr(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        call_id="call-abc-123",
        direction="inbound",
        caller_number="+15551234567",
        caller_name="John Doe",
        called_number="+15559876543",
        extension_id=uuid.uuid4(),
        did_id=uuid.uuid4(),
        trunk_id=uuid.uuid4(),
        ring_group_id=None,
        queue_id=None,
        disposition="answered",
        hangup_cause="normal_clearing",
        duration_seconds=120,
        billable_seconds=115,
        ring_seconds=5,
        start_time=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
        answer_time=datetime(2024, 1, 1, 10, 0, 5, tzinfo=UTC),
        end_time=datetime(2024, 1, 1, 10, 2, 0, tzinfo=UTC),
        has_recording=False,
        agent_disposition_code_id=None,
        agent_disposition_notes=None,
        disposition_entered_at=None,
        site_id=None,
        crm_customer_name=None,
        crm_company_name=None,
        crm_account_number=None,
        crm_matched_at=None,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListCdrs:
    async def test_returns_cdrs(self, mock_db):
        c1 = _make_cdr()
        c2 = _make_cdr()
        mock_db.execute.return_value = make_scalars_result([c1, c2])

        service = CDRService(mock_db)
        result = await service.list_cdrs(TENANT_ACME_ID, CDRFilter())
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = CDRService(mock_db)
        result = await service.list_cdrs(TENANT_ACME_ID, CDRFilter())
        assert result == []

    async def test_filters_by_direction(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([_make_cdr(direction="inbound")])
        service = CDRService(mock_db)
        filters = CDRFilter(direction="inbound")
        result = await service.list_cdrs(TENANT_ACME_ID, filters)
        assert len(result) == 1

    async def test_filters_by_date_range(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([_make_cdr()])
        service = CDRService(mock_db)
        filters = CDRFilter(
            date_from=datetime(2024, 1, 1, tzinfo=UTC),
            date_to=datetime(2024, 1, 2, tzinfo=UTC),
        )
        result = await service.list_cdrs(TENANT_ACME_ID, filters)
        assert len(result) == 1

    async def test_filters_by_crm_matched(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = CDRService(mock_db)
        filters = CDRFilter(crm_matched=True)
        result = await service.list_cdrs(TENANT_ACME_ID, filters)
        assert result == []


class TestGetCdr:
    async def test_found(self, mock_db):
        cdr = _make_cdr()
        mock_db.execute.return_value = make_scalar_result(cdr)
        service = CDRService(mock_db)
        result = await service.get_cdr(TENANT_ACME_ID, cdr.id)
        assert result is cdr

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = CDRService(mock_db)
        result = await service.get_cdr(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestSetDisposition:
    async def test_success(self, mock_db):
        cdr = _make_cdr()
        code = MagicMock()
        code.id = uuid.uuid4()
        code.tenant_id = TENANT_ACME_ID
        mock_db.execute.side_effect = [
            make_scalar_result(cdr),   # get_cdr
            make_scalar_result(code),  # verify disposition code
        ]

        service = CDRService(mock_db)
        await service.set_disposition(TENANT_ACME_ID, cdr.id, code.id, notes="Follow up needed")
        assert cdr.agent_disposition_code_id == code.id
        assert cdr.agent_disposition_notes == "Follow up needed"
        assert cdr.disposition_entered_at is not None
        mock_db.commit.assert_awaited_once()

    async def test_cdr_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = CDRService(mock_db)
        with pytest.raises(ValueError, match="CDR not found"):
            await service.set_disposition(TENANT_ACME_ID, uuid.uuid4(), uuid.uuid4())

    async def test_disposition_code_not_found_raises(self, mock_db):
        cdr = _make_cdr()
        mock_db.execute.side_effect = [
            make_scalar_result(cdr),
            make_scalar_result(None),  # code not found
        ]
        service = CDRService(mock_db)
        with pytest.raises(ValueError, match="Disposition code not found"):
            await service.set_disposition(TENANT_ACME_ID, cdr.id, uuid.uuid4())
