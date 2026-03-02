"""Tests for new_phone.services.security_config_service — security config CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.security_config_service import SecurityConfigService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_config(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        silent_intercom_enabled=True,
        silent_intercom_max_seconds=300,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_target(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        security_config_id=uuid.uuid4(),
        target_type="webhook",
        target_value="https://example.com/webhook",
        priority=1,
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

        service = SecurityConfigService(mock_db)
        result = await service.get_config(TENANT_ACME_ID)
        assert result.tenant_id == TENANT_ACME_ID

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SecurityConfigService(mock_db)
        result = await service.get_config(TENANT_ACME_ID)
        assert result is None


class TestCreateOrUpdate:
    async def test_creates_new_config(self, mock_db):
        # get_config returns None (first execute), then flush/commit
        mock_db.execute.return_value = make_scalar_result(None)

        data = MagicMock()
        data.model_dump.return_value = {"silent_intercom_enabled": True}

        service = SecurityConfigService(mock_db)
        await service.create_or_update(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_updates_existing_config(self, mock_db):
        existing = _make_config()
        mock_db.execute.return_value = make_scalar_result(existing)

        data = MagicMock()
        data.model_dump.return_value = {"silent_intercom_max_seconds": 600}

        service = SecurityConfigService(mock_db)
        result = await service.create_or_update(TENANT_ACME_ID, data)
        assert result.silent_intercom_max_seconds == 600
        mock_db.commit.assert_awaited()


class TestListNotificationTargets:
    async def test_returns_list(self, mock_db):
        t1 = _make_target()
        t2 = _make_target()
        mock_db.execute.return_value = make_scalars_result([t1, t2])

        service = SecurityConfigService(mock_db)
        result = await service.list_notification_targets(TENANT_ACME_ID, uuid.uuid4())
        assert len(result) == 2

    async def test_returns_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = SecurityConfigService(mock_db)
        result = await service.list_notification_targets(TENANT_ACME_ID, uuid.uuid4())
        assert result == []


class TestAddNotificationTarget:
    async def test_success(self, mock_db):
        config = _make_config()
        config_id = config.id
        # get_config returns config
        mock_db.execute.return_value = make_scalar_result(config)

        data = MagicMock()
        data.model_dump.return_value = {
            "target_type": "webhook",
            "target_value": "https://example.com",
            "priority": 1,
            "is_active": True,
        }

        service = SecurityConfigService(mock_db)
        await service.add_notification_target(TENANT_ACME_ID, config_id, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_config_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)

        data = MagicMock()
        service = SecurityConfigService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.add_notification_target(TENANT_ACME_ID, uuid.uuid4(), data)


class TestRemoveNotificationTarget:
    async def test_success(self, mock_db):
        target = _make_target()
        mock_db.execute.return_value = make_scalar_result(target)

        service = SecurityConfigService(mock_db)
        await service.remove_notification_target(TENANT_ACME_ID, target.id)
        mock_db.delete.assert_awaited()
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SecurityConfigService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.remove_notification_target(TENANT_ACME_ID, uuid.uuid4())
