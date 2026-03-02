"""Tests for new_phone.services.camp_on_service — camp-on request CRUD."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from new_phone.services.camp_on_service import CampOnService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_config(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        enabled=True,
        is_active=True,
        feature_code="*83",
        timeout_minutes=15,
        max_camp_ons_per_target=3,
        callback_retry_delay_seconds=30,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_request(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        caller_extension_id=uuid.uuid4(),
        target_extension_id=uuid.uuid4(),
        caller_extension_number="100",
        target_extension_number="200",
        caller_sip_username="sip-100",
        target_sip_username="sip-200",
        status="pending",
        reason=None,
        original_call_id=None,
        expires_at=None,
        cancelled_at=None,
        callback_initiated_at=None,
        connected_at=None,
        callback_attempts=0,
        created_at=None,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_extension(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        extension_number="100",
        sip_username="sip-100",
        is_active=True,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestGetConfig:
    async def test_found(self, mock_db):
        config = _make_config()
        mock_db.execute.return_value = make_scalar_result(config)

        service = CampOnService(mock_db)
        result = await service.get_config(TENANT_ACME_ID)
        assert result.enabled is True

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = CampOnService(mock_db)
        result = await service.get_config(TENANT_ACME_ID)
        assert result is None


class TestCreateConfig:
    async def test_success(self, mock_db):
        # get_config returns None (no existing)
        mock_db.execute.return_value = make_scalar_result(None)

        data = MagicMock()
        data.enabled = True
        data.feature_code = "*83"
        data.timeout_minutes = 15
        data.max_camp_ons_per_target = 3
        data.callback_retry_delay_seconds = 30

        service = CampOnService(mock_db)
        await service.create_config(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_raises(self, mock_db):
        existing = _make_config()
        mock_db.execute.return_value = make_scalar_result(existing)

        data = MagicMock()
        service = CampOnService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_config(TENANT_ACME_ID, data)


class TestUpdateConfig:
    async def test_success(self, mock_db):
        config = _make_config()
        mock_db.execute.return_value = make_scalar_result(config)

        data = MagicMock()
        data.model_dump.return_value = {"timeout_minutes": 30}

        service = CampOnService(mock_db)
        result = await service.update_config(config.id, data)
        assert result.timeout_minutes == 30
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = MagicMock()
        data.model_dump.return_value = {}

        service = CampOnService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.update_config(uuid.uuid4(), data)


class TestCancelRequest:
    async def test_success(self, mock_db):
        request = _make_request(status="pending")
        mock_db.execute.return_value = make_scalar_result(request)

        service = CampOnService(mock_db, redis=None)
        with (
            patch("new_phone.services.camp_on_service.CampOnStatus") as mock_status,
            patch.object(service, "_remove_from_redis", new_callable=AsyncMock),
            patch.object(service, "_publish_event", new_callable=AsyncMock),
        ):
            mock_status.pending.value = "pending"
            mock_status.cancelled.value = "cancelled"
            result = await service.cancel_request(TENANT_ACME_ID, request.id)

        assert result.status == "cancelled"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = CampOnService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.cancel_request(TENANT_ACME_ID, uuid.uuid4())


class TestListRequests:
    async def test_returns_list(self, mock_db):
        r1 = _make_request()
        r2 = _make_request()
        mock_db.execute.return_value = make_scalars_result([r1, r2])

        service = CampOnService(mock_db)
        result = await service.list_requests(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_returns_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = CampOnService(mock_db)
        result = await service.list_requests(TENANT_ACME_ID)
        assert result == []


class TestGetRequest:
    async def test_found(self, mock_db):
        request = _make_request()
        mock_db.execute.return_value = make_scalar_result(request)

        service = CampOnService(mock_db)
        result = await service.get_request(TENANT_ACME_ID, request.id)
        assert result.id == request.id

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = CampOnService(mock_db)
        result = await service.get_request(TENANT_ACME_ID, uuid.uuid4())
        assert result is None
