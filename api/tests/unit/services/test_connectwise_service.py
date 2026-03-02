"""Tests for new_phone.services.connectwise_service — ConnectWise CRUD + mappings."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from new_phone.services.connectwise_service import ConnectWiseService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_config(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        company_id="acme_company",
        public_key_encrypted="enc-pub",
        private_key_encrypted="enc-priv",
        client_id="cw-client-id",
        base_url="https://api.connectwise.com",
        api_version="2021.1",
        is_active=True,
        default_board_id=1,
        default_status_id=1,
        default_type_id=1,
        auto_ticket_missed_calls=True,
        auto_ticket_voicemails=True,
        auto_ticket_completed_calls=False,
        min_call_duration_seconds=30,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_mapping(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        cw_config_id=uuid.uuid4(),
        cw_company_id=12345,
        cw_company_name="Acme Corp",
        extension_id=uuid.uuid4(),
        did_id=None,
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

        service = ConnectWiseService(mock_db)
        result = await service.get_config(TENANT_ACME_ID)
        assert result.company_id == "acme_company"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ConnectWiseService(mock_db)
        result = await service.get_config(TENANT_ACME_ID)
        assert result is None


class TestCreateConfig:
    async def test_success(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)

        data = MagicMock()
        data.company_id = "acme"
        data.public_key = "pub-key"
        data.private_key = "priv-key"
        data.client_id = "client"
        data.base_url = "https://api.connectwise.com"
        data.api_version = "2021.1"
        data.default_board_id = 1
        data.default_status_id = 1
        data.default_type_id = 1
        data.auto_ticket_missed_calls = True
        data.auto_ticket_voicemails = True
        data.auto_ticket_completed_calls = False
        data.min_call_duration_seconds = 30

        service = ConnectWiseService(mock_db)
        with patch("new_phone.services.connectwise_service.encrypt_value", return_value="encrypted"):
            await service.create_config(TENANT_ACME_ID, data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_raises(self, mock_db):
        existing = _make_config()
        mock_db.execute.return_value = make_scalar_result(existing)

        data = MagicMock()
        service = ConnectWiseService(mock_db)
        with pytest.raises(ValueError, match="already configured"):
            await service.create_config(TENANT_ACME_ID, data)


class TestUpdateConfig:
    async def test_success(self, mock_db):
        config = _make_config()
        mock_db.execute.return_value = make_scalar_result(config)

        data = MagicMock()
        data.model_dump.return_value = {"default_board_id": 99}

        service = ConnectWiseService(mock_db)
        result = await service.update_config(config.id, data)
        assert result.default_board_id == 99
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = MagicMock()
        data.model_dump.return_value = {}

        service = ConnectWiseService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.update_config(uuid.uuid4(), data)


class TestDeleteConfig:
    async def test_success(self, mock_db):
        config = _make_config()
        mock_db.execute.return_value = make_scalar_result(config)

        service = ConnectWiseService(mock_db)
        await service.delete_config(config.id)
        mock_db.delete.assert_awaited()
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ConnectWiseService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.delete_config(uuid.uuid4())


class TestListCompanyMappings:
    async def test_returns_list(self, mock_db):
        m1 = _make_mapping()
        m2 = _make_mapping()
        mock_db.execute.return_value = make_scalars_result([m1, m2])

        service = ConnectWiseService(mock_db)
        result = await service.list_company_mappings(uuid.uuid4())
        assert len(result) == 2

    async def test_returns_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = ConnectWiseService(mock_db)
        result = await service.list_company_mappings(uuid.uuid4())
        assert result == []


class TestAddCompanyMapping:
    async def test_success(self, mock_db):
        data = MagicMock()
        data.cw_company_id = 12345
        data.cw_company_name = "Acme Corp"
        data.extension_id = uuid.uuid4()
        data.did_id = None

        service = ConnectWiseService(mock_db)
        await service.add_company_mapping(uuid.uuid4(), data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_no_extension_or_did_raises(self, mock_db):
        data = MagicMock()
        data.extension_id = None
        data.did_id = None

        service = ConnectWiseService(mock_db)
        with pytest.raises(ValueError, match="At least one"):
            await service.add_company_mapping(uuid.uuid4(), data)


class TestRemoveCompanyMapping:
    async def test_success(self, mock_db):
        mapping = _make_mapping()
        mock_db.execute.return_value = make_scalar_result(mapping)

        service = ConnectWiseService(mock_db)
        await service.remove_company_mapping(mapping.id)
        mock_db.delete.assert_awaited()
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ConnectWiseService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.remove_company_mapping(uuid.uuid4())
