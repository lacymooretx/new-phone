"""Tests for new_phone.services.cdr_service — CDR listing, filtering, CSV export."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from new_phone.services.cdr_service import CDRService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_cdr(**overrides):
    cdr = MagicMock()
    cdr.id = overrides.get("id", uuid.uuid4())
    cdr.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    cdr.call_id = overrides.get("call_id", str(uuid.uuid4()))
    cdr.direction = overrides.get("direction", "inbound")
    cdr.caller_number = overrides.get("caller_number", "+15551234567")
    cdr.caller_name = overrides.get("caller_name", "Test Caller")
    cdr.called_number = overrides.get("called_number", "100")
    cdr.disposition = overrides.get("disposition", "answered")
    cdr.hangup_cause = overrides.get("hangup_cause", "NORMAL_CLEARING")
    cdr.duration_seconds = overrides.get("duration_seconds", 120)
    cdr.billable_seconds = overrides.get("billable_seconds", 115)
    cdr.ring_seconds = overrides.get("ring_seconds", 5)
    cdr.start_time = overrides.get("start_time", datetime(2024, 6, 1, 12, 0, tzinfo=UTC))
    cdr.answer_time = overrides.get("answer_time", datetime(2024, 6, 1, 12, 0, 5, tzinfo=UTC))
    cdr.end_time = overrides.get("end_time", datetime(2024, 6, 1, 12, 2, 0, tzinfo=UTC))
    cdr.has_recording = overrides.get("has_recording", False)
    cdr.crm_customer_name = overrides.get("crm_customer_name")
    cdr.crm_company_name = overrides.get("crm_company_name")
    cdr.crm_account_number = overrides.get("crm_account_number")
    cdr.crm_provider_type = overrides.get("crm_provider_type")
    cdr.crm_deep_link_url = overrides.get("crm_deep_link_url")
    return cdr


def _make_filter(**overrides):
    from new_phone.schemas.cdr import CDRFilter

    defaults = dict(
        date_from=None,
        date_to=None,
        extension_id=None,
        direction=None,
        disposition=None,
        agent_disposition_code_id=None,
        site_id=None,
        crm_customer_name=None,
        crm_company_name=None,
        crm_account_number=None,
        crm_matched=None,
        offset=0,
        limit=50,
    )
    defaults.update(overrides)
    return CDRFilter(**defaults)


class TestListCdrs:
    async def test_returns_list(self, mock_db):
        c1 = _make_cdr(caller_number="+15551111111")
        c2 = _make_cdr(caller_number="+15552222222")
        mock_db.execute.return_value = make_scalars_result([c1, c2])

        service = CDRService(mock_db)
        result = await service.list_cdrs(TENANT_ACME_ID, _make_filter())
        assert len(result) == 2

    async def test_returns_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = CDRService(mock_db)
        result = await service.list_cdrs(TENANT_ACME_ID, _make_filter())
        assert result == []

    async def test_with_direction_filter(self, mock_db):
        c1 = _make_cdr(direction="inbound")
        mock_db.execute.return_value = make_scalars_result([c1])
        service = CDRService(mock_db)
        result = await service.list_cdrs(TENANT_ACME_ID, _make_filter(direction="inbound"))
        assert len(result) == 1

    async def test_with_date_filter(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = CDRService(mock_db)
        result = await service.list_cdrs(
            TENANT_ACME_ID,
            _make_filter(
                date_from=datetime(2024, 1, 1, tzinfo=UTC),
                date_to=datetime(2024, 12, 31, tzinfo=UTC),
            ),
        )
        assert result == []
        mock_db.execute.assert_awaited()


class TestGetCdr:
    async def test_found(self, mock_db):
        cdr = _make_cdr()
        mock_db.execute.return_value = make_scalar_result(cdr)
        service = CDRService(mock_db)
        result = await service.get_cdr(TENANT_ACME_ID, cdr.id)
        assert result.call_id == cdr.call_id

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = CDRService(mock_db)
        result = await service.get_cdr(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestExportCsv:
    async def test_returns_csv_string(self, mock_db):
        c1 = _make_cdr(caller_number="+15551111111", direction="inbound")
        mock_db.execute.return_value = make_scalars_result([c1])

        service = CDRService(mock_db)
        csv_str = await service.export_csv(TENANT_ACME_ID, _make_filter())
        assert "call_id" in csv_str  # header row
        assert "+15551111111" in csv_str
        assert "inbound" in csv_str

    async def test_empty_export(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = CDRService(mock_db)
        csv_str = await service.export_csv(TENANT_ACME_ID, _make_filter())
        # Should still have header row
        assert "call_id" in csv_str
        lines = csv_str.strip().split("\n")
        assert len(lines) == 1  # header only


class TestSetDisposition:
    async def test_success(self, mock_db):
        cdr = _make_cdr()
        code = MagicMock()
        code.id = uuid.uuid4()
        mock_db.execute.side_effect = [
            make_scalar_result(cdr),  # get_cdr
            make_scalar_result(code),  # verify disposition code
        ]

        service = CDRService(mock_db)
        await service.set_disposition(TENANT_ACME_ID, cdr.id, code.id, notes="Resolved")
        assert cdr.agent_disposition_code_id == code.id

    async def test_cdr_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = CDRService(mock_db)
        with pytest.raises(ValueError, match="CDR not found"):
            await service.set_disposition(TENANT_ACME_ID, uuid.uuid4(), uuid.uuid4())


class TestCleanupOldCdrs:
    async def test_returns_rowcount(self, mock_db):
        from tests.unit.conftest import make_rowcount_result

        mock_db.execute.return_value = make_rowcount_result(42)
        service = CDRService(mock_db)
        count = await service.cleanup_old_cdrs(datetime(2023, 1, 1, tzinfo=UTC))
        assert count == 42
