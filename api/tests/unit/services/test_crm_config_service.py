"""Tests for new_phone.services.crm_config_service — CRM config CRUD."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from new_phone.services.crm_config_service import CRMConfigService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result


def _make_config(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        provider_type="hubspot",
        encrypted_credentials="encrypted-json",
        base_url="https://api.hubapi.com",
        cache_ttl_seconds=300,
        lookup_timeout_seconds=5,
        enrichment_enabled=True,
        enrich_inbound=True,
        enrich_outbound=False,
        custom_fields_map=None,
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

        service = CRMConfigService(mock_db)
        result = await service.get_config(TENANT_ACME_ID)
        assert result.provider_type == "hubspot"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = CRMConfigService(mock_db)
        result = await service.get_config(TENANT_ACME_ID)
        assert result is None


class TestCreateConfig:
    async def test_success(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)

        data = MagicMock()
        data.provider_type = "hubspot"
        data.credentials = {"api_key": "test-key"}
        data.base_url = "https://api.hubapi.com"
        data.cache_ttl_seconds = 300
        data.lookup_timeout_seconds = 5
        data.enrichment_enabled = True
        data.enrich_inbound = True
        data.enrich_outbound = False
        data.custom_fields_map = None

        service = CRMConfigService(mock_db)
        with patch("new_phone.services.crm_config_service.encrypt_value", return_value="encrypted"):
            await service.create_config(TENANT_ACME_ID, data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_raises(self, mock_db):
        existing = _make_config()
        mock_db.execute.return_value = make_scalar_result(existing)

        data = MagicMock()
        service = CRMConfigService(mock_db)
        with pytest.raises(ValueError, match="already configured"):
            await service.create_config(TENANT_ACME_ID, data)


class TestUpdateConfig:
    async def test_success(self, mock_db):
        config = _make_config()
        mock_db.execute.return_value = make_scalar_result(config)

        data = MagicMock()
        data.model_dump.return_value = {"enrichment_enabled": False}

        service = CRMConfigService(mock_db)
        result = await service.update_config(config.id, data)
        assert result.enrichment_enabled is False
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = MagicMock()
        data.model_dump.return_value = {}

        service = CRMConfigService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.update_config(uuid.uuid4(), data)


class TestDeleteConfig:
    async def test_success(self, mock_db):
        config = _make_config()
        mock_db.execute.return_value = make_scalar_result(config)

        service = CRMConfigService(mock_db)
        await service.delete_config(config.id)
        mock_db.delete.assert_awaited()
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = CRMConfigService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.delete_config(uuid.uuid4())


class TestInvalidateCache:
    async def test_with_phone_number(self, mock_db):
        redis = AsyncMock()
        redis.delete.return_value = 1

        service = CRMConfigService(mock_db, redis=redis)
        result = await service.invalidate_cache(TENANT_ACME_ID, phone_number="+15551234567")
        assert result == 1
        redis.delete.assert_awaited()

    async def test_no_redis_returns_zero(self, mock_db):
        service = CRMConfigService(mock_db, redis=None)
        result = await service.invalidate_cache(TENANT_ACME_ID)
        assert result == 0
