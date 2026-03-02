"""Tests for new_phone.services.port_service — port request lifecycle."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from new_phone.models.port_request import PortRequestStatus
from new_phone.schemas.port_requests import PortRequestCreate, PortRequestUpdate
from new_phone.services.port_service import PortService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_port_request(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        numbers=["+15551234567"],
        current_carrier="AT&T",
        status=PortRequestStatus.SUBMITTED,
        provider="clearlyip",
        provider_port_id=None,
        loa_file_path=None,
        foc_date=None,
        requested_port_date=None,
        actual_port_date=None,
        rejection_reason=None,
        notes=None,
        submitted_by=None,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ── list_port_requests ───────────────────────────────────────────────────


class TestListPortRequests:
    async def test_returns_requests(self, mock_db):
        pr1 = _make_port_request()
        pr2 = _make_port_request()
        mock_db.execute.return_value = make_scalars_result([pr1, pr2])

        service = PortService(mock_db)
        result = await service.list_port_requests(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = PortService(mock_db)
        result = await service.list_port_requests(TENANT_ACME_ID)
        assert result == []

    async def test_filters_by_status(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([_make_port_request()])
        service = PortService(mock_db)
        result = await service.list_port_requests(
            TENANT_ACME_ID, status_filter="submitted"
        )
        assert len(result) == 1


# ── get_port_request ─────────────────────────────────────────────────────


class TestGetPortRequest:
    async def test_found(self, mock_db):
        pr = _make_port_request()
        mock_db.execute.return_value = make_scalar_result(pr)
        service = PortService(mock_db)
        result = await service.get_port_request(TENANT_ACME_ID, pr.id)
        assert result is pr

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = PortService(mock_db)
        result = await service.get_port_request(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


# ── submit_port_request ──────────────────────────────────────────────────


class TestSubmitPortRequest:
    async def test_success(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])  # no active overlaps
        mock_db.flush = AsyncMock()
        data = PortRequestCreate(
            numbers=["+15559876543"],
            current_carrier="Verizon",
            provider="clearlyip",
        )

        service = PortService(mock_db)
        await service.submit_port_request(TENANT_ACME_ID, data)
        # port_request + history = 2 adds
        assert mock_db.add.call_count == 2
        mock_db.flush.assert_awaited()
        mock_db.commit.assert_awaited_once()

    async def test_invalid_number_format_raises(self, mock_db):
        data = PortRequestCreate(
            numbers=["5551234567"],  # missing +
            current_carrier="AT&T",
            provider="clearlyip",
        )
        service = PortService(mock_db)
        with pytest.raises(ValueError, match=r"E\.164"):
            await service.submit_port_request(TENANT_ACME_ID, data)

    async def test_overlapping_numbers_raises(self, mock_db):
        existing = _make_port_request(
            numbers=["+15551234567"],
            status=PortRequestStatus.SUBMITTED,
        )
        mock_db.execute.return_value = make_scalars_result([existing])

        data = PortRequestCreate(
            numbers=["+15551234567"],
            current_carrier="AT&T",
            provider="clearlyip",
        )
        service = PortService(mock_db)
        with pytest.raises(ValueError, match="already in an active port"):
            await service.submit_port_request(TENANT_ACME_ID, data)


# ── update_port_request ──────────────────────────────────────────────────


class TestUpdatePortRequest:
    async def test_success(self, mock_db):
        pr = _make_port_request(status=PortRequestStatus.SUBMITTED)
        mock_db.execute.return_value = make_scalar_result(pr)
        data = PortRequestUpdate(notes="Updated notes")

        service = PortService(mock_db)
        await service.update_port_request(TENANT_ACME_ID, pr.id, data)
        assert pr.notes == "Updated notes"
        mock_db.commit.assert_awaited_once()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = PortService(mock_db)
        with pytest.raises(ValueError, match="Port request not found"):
            await service.update_port_request(
                TENANT_ACME_ID, uuid.uuid4(), PortRequestUpdate(notes="x")
            )

    async def test_completed_cannot_update(self, mock_db):
        pr = _make_port_request(status=PortRequestStatus.COMPLETED)
        mock_db.execute.return_value = make_scalar_result(pr)
        service = PortService(mock_db)
        with pytest.raises(ValueError, match="Cannot update"):
            await service.update_port_request(
                TENANT_ACME_ID, pr.id, PortRequestUpdate(notes="x")
            )


# ── update_status (valid + invalid transitions) ─────────────────────────


class TestUpdateStatusTransitions:
    async def test_valid_transition_submitted_to_pending_loa(self, mock_db):
        pr = _make_port_request(status=PortRequestStatus.SUBMITTED)
        mock_db.execute.return_value = make_scalar_result(pr)
        data = PortRequestUpdate(status=PortRequestStatus.PENDING_LOA)

        service = PortService(mock_db)
        await service.update_port_request(TENANT_ACME_ID, pr.id, data)
        assert pr.status == PortRequestStatus.PENDING_LOA

    async def test_invalid_transition_raises(self, mock_db):
        pr = _make_port_request(status=PortRequestStatus.SUBMITTED)
        mock_db.execute.return_value = make_scalar_result(pr)
        data = PortRequestUpdate(status=PortRequestStatus.COMPLETED)

        service = PortService(mock_db)
        with pytest.raises(ValueError, match="Invalid status transition"):
            await service.update_port_request(TENANT_ACME_ID, pr.id, data)


# ── upload_loa ───────────────────────────────────────────────────────────


class TestUploadLoa:
    async def test_wrong_status_from_submitted_raises(self, mock_db):
        """submitted -> loa_submitted is not a valid transition; must go via pending_loa."""
        pr = _make_port_request(status=PortRequestStatus.SUBMITTED)
        mock_db.execute.return_value = make_scalar_result(pr)

        service = PortService(mock_db)
        with pytest.raises(ValueError, match="Invalid status transition"):
            await service.upload_loa(TENANT_ACME_ID, pr.id, "/uploads/loa.pdf")

    async def test_success_from_pending_loa(self, mock_db):
        pr = _make_port_request(status=PortRequestStatus.PENDING_LOA)
        mock_db.execute.return_value = make_scalar_result(pr)

        service = PortService(mock_db)
        await service.upload_loa(TENANT_ACME_ID, pr.id, "/uploads/loa.pdf")
        assert pr.status == PortRequestStatus.LOA_SUBMITTED
        assert pr.loa_file_path == "/uploads/loa.pdf"

    async def test_wrong_status_raises(self, mock_db):
        pr = _make_port_request(status=PortRequestStatus.FOC_RECEIVED)
        mock_db.execute.return_value = make_scalar_result(pr)
        service = PortService(mock_db)
        with pytest.raises(ValueError, match="Cannot upload LOA"):
            await service.upload_loa(TENANT_ACME_ID, pr.id, "/path")


# ── check_status ─────────────────────────────────────────────────────────


class TestCheckStatus:
    async def test_returns_current_state(self, mock_db):
        pr = _make_port_request(status=PortRequestStatus.LOA_SUBMITTED)
        mock_db.execute.return_value = make_scalar_result(pr)

        service = PortService(mock_db)
        result = await service.check_status(TENANT_ACME_ID, pr.id)
        assert result.status == PortRequestStatus.LOA_SUBMITTED

    async def test_completed_returns_immediately(self, mock_db):
        pr = _make_port_request(status=PortRequestStatus.COMPLETED)
        mock_db.execute.return_value = make_scalar_result(pr)

        service = PortService(mock_db)
        result = await service.check_status(TENANT_ACME_ID, pr.id)
        assert result.status == PortRequestStatus.COMPLETED

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = PortService(mock_db)
        with pytest.raises(ValueError, match="Port request not found"):
            await service.check_status(TENANT_ACME_ID, uuid.uuid4())


# ── cancel_port ──────────────────────────────────────────────────────────


class TestCancelPort:
    async def test_success(self, mock_db):
        pr = _make_port_request(status=PortRequestStatus.SUBMITTED)
        mock_db.execute.return_value = make_scalar_result(pr)

        service = PortService(mock_db)
        await service.cancel_port(TENANT_ACME_ID, pr.id)
        assert pr.status == PortRequestStatus.CANCELLED
        mock_db.commit.assert_awaited()

    async def test_already_completed_raises(self, mock_db):
        pr = _make_port_request(status=PortRequestStatus.COMPLETED)
        mock_db.execute.return_value = make_scalar_result(pr)
        service = PortService(mock_db)
        with pytest.raises(ValueError, match="Cannot cancel"):
            await service.cancel_port(TENANT_ACME_ID, pr.id)

    async def test_already_cancelled_raises(self, mock_db):
        pr = _make_port_request(status=PortRequestStatus.CANCELLED)
        mock_db.execute.return_value = make_scalar_result(pr)
        service = PortService(mock_db)
        with pytest.raises(ValueError, match="Cannot cancel"):
            await service.cancel_port(TENANT_ACME_ID, pr.id)


# ── complete_port ────────────────────────────────────────────────────────


class TestCompletePort:
    async def test_success_creates_dids(self, mock_db):
        pr = _make_port_request(
            status=PortRequestStatus.IN_PROGRESS,
            numbers=["+15551111111", "+15552222222"],
        )
        mock_db.execute.side_effect = [
            make_scalar_result(pr),      # get_port_request
            make_scalar_result(None),    # DID exists check #1
            make_scalar_result(None),    # DID exists check #2
        ]

        service = PortService(mock_db)
        await service.complete_port(TENANT_ACME_ID, pr.id)
        assert pr.status == PortRequestStatus.COMPLETED
        # 2 DIDs + 1 history = 3 adds
        assert mock_db.add.call_count == 3
        mock_db.commit.assert_awaited()

    async def test_wrong_status_raises(self, mock_db):
        pr = _make_port_request(status=PortRequestStatus.SUBMITTED)
        mock_db.execute.return_value = make_scalar_result(pr)
        service = PortService(mock_db)
        with pytest.raises(ValueError, match="in_progress"):
            await service.complete_port(TENANT_ACME_ID, pr.id)

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = PortService(mock_db)
        with pytest.raises(ValueError, match="Port request not found"):
            await service.complete_port(TENANT_ACME_ID, uuid.uuid4())

    async def test_skips_existing_dids(self, mock_db):
        pr = _make_port_request(
            status=PortRequestStatus.IN_PROGRESS,
            numbers=["+15551111111"],
        )
        existing_did = MagicMock()
        mock_db.execute.side_effect = [
            make_scalar_result(pr),            # get_port_request
            make_scalar_result(existing_did),  # DID already exists
        ]

        service = PortService(mock_db)
        await service.complete_port(TENANT_ACME_ID, pr.id)
        # Only 1 history entry, no DID added
        assert mock_db.add.call_count == 1
