"""Tests for new_phone.services.recording_tier_service — recording tiering config CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.recording_tier_service import RecordingTierService
from tests.unit.conftest import (
    TENANT_ACME_ID,
    USER_ACME_ADMIN_ID,
    make_scalar_result,
)


def _make_tier_config(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        hot_tier_days=30,
        cold_tier_retention_days=365,
        retrieval_cache_days=7,
        auto_tier_enabled=True,
        auto_delete_enabled=False,
        is_active=True,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestGetConfig:
    async def test_found(self, mock_db):
        config = _make_tier_config()
        mock_db.execute.return_value = make_scalar_result(config)

        service = RecordingTierService(mock_db)
        result = await service.get_config(TENANT_ACME_ID)
        assert result.hot_tier_days == 30

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = RecordingTierService(mock_db)
        result = await service.get_config(TENANT_ACME_ID)
        assert result is None


class TestCreateConfig:
    async def test_success(self, mock_db):
        # get_config returns None
        mock_db.execute.return_value = make_scalar_result(None)

        data = MagicMock()
        data.hot_tier_days = 30
        data.cold_tier_retention_days = 365
        data.retrieval_cache_days = 7
        data.auto_tier_enabled = True
        data.auto_delete_enabled = False

        service = RecordingTierService(mock_db)
        await service.create_config(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_raises(self, mock_db):
        existing = _make_tier_config()
        mock_db.execute.return_value = make_scalar_result(existing)

        data = MagicMock()
        service = RecordingTierService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_config(TENANT_ACME_ID, data)


class TestUpdateConfig:
    async def test_success(self, mock_db):
        config = _make_tier_config()
        mock_db.execute.return_value = make_scalar_result(config)

        data = MagicMock()
        data.model_dump.return_value = {"hot_tier_days": 60}

        service = RecordingTierService(mock_db)
        result = await service.update_config(config.id, data)
        assert result.hot_tier_days == 60
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = MagicMock()
        data.model_dump.return_value = {}

        service = RecordingTierService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.update_config(uuid.uuid4(), data)


class TestDeleteConfig:
    async def test_success(self, mock_db):
        config = _make_tier_config()
        mock_db.execute.return_value = make_scalar_result(config)

        service = RecordingTierService(mock_db)
        await service.delete_config(config.id)
        mock_db.delete.assert_awaited()
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = RecordingTierService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.delete_config(uuid.uuid4())


class TestSetLegalHold:
    async def test_success(self, mock_db):
        result_mock = MagicMock()
        result_mock.rowcount = 3
        mock_db.execute.return_value = result_mock

        service = RecordingTierService(mock_db)
        count = await service.set_legal_hold(
            TENANT_ACME_ID, [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()], True, USER_ACME_ADMIN_ID
        )
        assert count == 3
        mock_db.commit.assert_awaited()


class TestGetStorageStats:
    async def test_returns_stats(self, mock_db):
        hot_row = MagicMock()
        hot_row.storage_tier = "hot"
        hot_row.count = 100
        hot_row.total_bytes = 1000000

        cold_row = MagicMock()
        cold_row.storage_tier = "cold"
        cold_row.count = 500
        cold_row.total_bytes = 5000000

        tier_result = MagicMock()
        tier_result.all.return_value = [hot_row, cold_row]

        hold_result = MagicMock()
        hold_result.scalar.return_value = 10

        mock_db.execute.side_effect = [
            MagicMock(),  # set_tenant_context
            tier_result,
            hold_result,
        ]

        service = RecordingTierService(mock_db)
        stats = await service.get_storage_stats(TENANT_ACME_ID)
        assert stats["hot_count"] == 100
        assert stats["cold_count"] == 500
        assert stats["legal_hold_count"] == 10
        assert stats["total_bytes"] == 6000000
