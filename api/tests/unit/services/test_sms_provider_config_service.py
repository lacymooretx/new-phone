"""Tests for new_phone.services.sms_provider_config_service — SMS provider config CRUD."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from new_phone.services.sms_provider_config_service import SMSProviderConfigService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_sms_config(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        provider_type="twilio",
        label="Primary Twilio",
        encrypted_credentials="encrypted-json",
        is_default=True,
        is_active=True,
        notes=None,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListConfigs:
    async def test_returns_list(self, mock_db):
        c1 = _make_sms_config(label="Twilio")
        c2 = _make_sms_config(label="ClearlyIP")
        mock_db.execute.return_value = make_scalars_result([c1, c2])

        service = SMSProviderConfigService(mock_db)
        result = await service.list_configs(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_returns_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = SMSProviderConfigService(mock_db)
        result = await service.list_configs(TENANT_ACME_ID)
        assert result == []


class TestGetConfig:
    async def test_found(self, mock_db):
        config = _make_sms_config()
        mock_db.execute.return_value = make_scalar_result(config)

        service = SMSProviderConfigService(mock_db)
        result = await service.get_config(TENANT_ACME_ID, config.id)
        assert result.label == "Primary Twilio"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SMSProviderConfigService(mock_db)
        result = await service.get_config(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateConfig:
    async def test_success(self, mock_db):
        data = MagicMock()
        data.provider_type = "twilio"
        data.label = "New Config"
        data.credentials = {"account_sid": "ACxx", "auth_token": "tok"}
        data.is_default = False
        data.notes = None

        service = SMSProviderConfigService(mock_db)
        with patch("new_phone.services.sms_provider_config_service.encrypt_value", return_value="encrypted"):
            await service.create_config(TENANT_ACME_ID, data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_sets_default_unsets_existing(self, mock_db):
        existing = _make_sms_config(is_default=True)
        # _unset_defaults query then _unset_defaults scalars
        unset_result = make_scalars_result([existing])

        data = MagicMock()
        data.provider_type = "twilio"
        data.label = "New Default"
        data.credentials = {"key": "val"}
        data.is_default = True
        data.notes = None

        mock_db.execute.return_value = unset_result

        service = SMSProviderConfigService(mock_db)
        with patch("new_phone.services.sms_provider_config_service.encrypt_value", return_value="encrypted"):
            await service.create_config(TENANT_ACME_ID, data)

        # The existing config should have had is_default set to False
        assert existing.is_default is False
        mock_db.add.assert_called()


class TestUpdateConfig:
    async def test_success(self, mock_db):
        config = _make_sms_config(label="Old Label")
        mock_db.execute.return_value = make_scalar_result(config)

        data = MagicMock()
        data.model_dump.return_value = {"label": "Updated Label"}

        service = SMSProviderConfigService(mock_db)
        result = await service.update_config(TENANT_ACME_ID, config.id, data)
        assert result.label == "Updated Label"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = MagicMock()
        data.model_dump.return_value = {}

        service = SMSProviderConfigService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.update_config(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeleteConfig:
    async def test_success(self, mock_db):
        config = _make_sms_config(is_active=True, is_default=True)
        mock_db.execute.return_value = make_scalar_result(config)

        service = SMSProviderConfigService(mock_db)
        result = await service.delete_config(TENANT_ACME_ID, config.id)
        assert result.is_active is False
        assert result.is_default is False
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SMSProviderConfigService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.delete_config(TENANT_ACME_ID, uuid.uuid4())


class TestGetDefaultConfig:
    async def test_found(self, mock_db):
        config = _make_sms_config(is_default=True)
        mock_db.execute.return_value = make_scalar_result(config)

        service = SMSProviderConfigService(mock_db)
        result = await service.get_default_config(TENANT_ACME_ID)
        assert result.is_default is True

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SMSProviderConfigService(mock_db)
        result = await service.get_default_config(TENANT_ACME_ID)
        assert result is None
