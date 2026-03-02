"""Tests for new_phone.services.sso_config_service — SSO provider CRUD."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from new_phone.services.sso_config_service import SSOConfigService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_provider(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        provider_type="microsoft",
        display_name="Entra ID",
        client_id="test-client-id",
        client_secret_encrypted="encrypted-secret",
        issuer_url="https://login.microsoftonline.com/tenant-id/v2.0",
        discovery_url="https://login.microsoftonline.com/tenant-id/v2.0/.well-known/openid-configuration",
        scopes=["openid", "profile", "email"],
        auto_provision=True,
        default_role="tenant_user",
        enforce_sso=False,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_mapping(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        sso_provider_id=uuid.uuid4(),
        external_group_id="group-123",
        external_group_name="Admins",
        pbx_role="tenant_admin",
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestGetProvider:
    async def test_found(self, mock_db):
        provider = _make_provider()
        mock_db.execute.return_value = make_scalar_result(provider)

        service = SSOConfigService(mock_db)
        result = await service.get_provider(TENANT_ACME_ID)
        assert result.provider_type == "microsoft"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SSOConfigService(mock_db)
        result = await service.get_provider(TENANT_ACME_ID)
        assert result is None


class TestCreateProvider:
    async def test_success(self, mock_db):
        # get_provider returns None
        mock_db.execute.return_value = make_scalar_result(None)

        data = MagicMock()
        data.provider_type = "microsoft"
        data.display_name = "Entra ID"
        data.client_id = "test-client-id"
        data.client_secret = "test-secret"
        data.issuer_url = "https://login.microsoftonline.com/tenant-id/v2.0"
        data.scopes = ["openid", "profile"]
        data.auto_provision = True
        data.default_role = "tenant_user"
        data.enforce_sso = False

        service = SSOConfigService(mock_db)
        with patch("new_phone.services.sso_config_service.encrypt_value", return_value="encrypted"):
            await service.create_provider(TENANT_ACME_ID, data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_raises(self, mock_db):
        existing = _make_provider()
        mock_db.execute.return_value = make_scalar_result(existing)

        data = MagicMock()
        service = SSOConfigService(mock_db)
        with pytest.raises(ValueError, match="already configured"):
            await service.create_provider(TENANT_ACME_ID, data)


class TestUpdateProvider:
    async def test_success(self, mock_db):
        provider = _make_provider()
        mock_db.execute.return_value = make_scalar_result(provider)

        data = MagicMock()
        data.model_dump.return_value = {"display_name": "Updated Name"}

        service = SSOConfigService(mock_db)
        result = await service.update_provider(provider.id, data)
        assert result.display_name == "Updated Name"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = MagicMock()
        data.model_dump.return_value = {}

        service = SSOConfigService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.update_provider(uuid.uuid4(), data)


class TestDeleteProvider:
    async def test_success(self, mock_db):
        provider = _make_provider()
        mock_db.execute.return_value = make_scalar_result(provider)

        service = SSOConfigService(mock_db)
        await service.delete_provider(provider.id)
        mock_db.delete.assert_awaited()
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SSOConfigService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.delete_provider(uuid.uuid4())


class TestListRoleMappings:
    async def test_returns_list(self, mock_db):
        m1 = _make_mapping()
        m2 = _make_mapping()
        mock_db.execute.return_value = make_scalars_result([m1, m2])

        service = SSOConfigService(mock_db)
        result = await service.list_role_mappings(uuid.uuid4())
        assert len(result) == 2


class TestRemoveRoleMapping:
    async def test_success(self, mock_db):
        mapping = _make_mapping()
        mock_db.execute.return_value = make_scalar_result(mapping)

        service = SSOConfigService(mock_db)
        await service.remove_role_mapping(mapping.id)
        mock_db.delete.assert_awaited()
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SSOConfigService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.remove_role_mapping(uuid.uuid4())
