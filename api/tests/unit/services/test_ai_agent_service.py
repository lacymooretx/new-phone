"""Tests for new_phone.services.ai_agent_service — AI agent provider/context/tool CRUD."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from new_phone.services.ai_agent_service import AIAgentService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_provider_config(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        provider_name="openai",
        api_key_encrypted="encrypted-key",
        base_url=None,
        model_id="gpt-4",
        extra_config=None,
        is_active=True,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_context(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        name="main-agent",
        display_name="Main Agent",
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_tool(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        name="lookup_customer",
        display_name="Lookup Customer",
        webhook_headers_encrypted=None,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListProviderConfigs:
    async def test_returns_list(self, mock_db):
        c1 = _make_provider_config(provider_name="openai")
        c2 = _make_provider_config(provider_name="deepgram")
        mock_db.execute.return_value = make_scalars_result([c1, c2])

        service = AIAgentService(mock_db)
        result = await service.list_provider_configs(TENANT_ACME_ID)
        assert len(result) == 2


class TestCreateProviderConfig:
    async def test_success(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)

        data = MagicMock()
        data.provider_name = "openai"
        data.api_key = "test-key"
        data.base_url = None
        data.model_id = "gpt-4"
        data.extra_config = None

        service = AIAgentService(mock_db)
        with patch("new_phone.services.ai_agent_service.encrypt_value", return_value="encrypted"):
            await service.create_provider_config(TENANT_ACME_ID, data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_raises(self, mock_db):
        existing = _make_provider_config()
        mock_db.execute.return_value = make_scalar_result(existing)

        data = MagicMock()
        data.provider_name = "openai"

        service = AIAgentService(mock_db)
        with pytest.raises(ValueError, match="already configured"):
            await service.create_provider_config(TENANT_ACME_ID, data)


class TestUpdateProviderConfig:
    async def test_success(self, mock_db):
        config = _make_provider_config()
        mock_db.execute.return_value = make_scalar_result(config)

        data = MagicMock()
        data.model_dump.return_value = {"model_id": "gpt-4o"}

        service = AIAgentService(mock_db)
        result = await service.update_provider_config(config.id, data)
        assert result.model_id == "gpt-4o"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = MagicMock()
        data.model_dump.return_value = {}

        service = AIAgentService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.update_provider_config(uuid.uuid4(), data)


class TestDeleteProviderConfig:
    async def test_success(self, mock_db):
        config = _make_provider_config()
        mock_db.execute.return_value = make_scalar_result(config)

        service = AIAgentService(mock_db)
        await service.delete_provider_config(config.id)
        mock_db.delete.assert_awaited()
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = AIAgentService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.delete_provider_config(uuid.uuid4())


class TestListContexts:
    async def test_returns_list(self, mock_db):
        c1 = _make_context(name="agent-a")
        c2 = _make_context(name="agent-b")
        mock_db.execute.return_value = make_scalars_result([c1, c2])

        service = AIAgentService(mock_db)
        result = await service.list_contexts(TENANT_ACME_ID)
        assert len(result) == 2


class TestCreateContext:
    async def test_success(self, mock_db):
        # get_context_by_name returns None
        mock_db.execute.return_value = make_scalar_result(None)

        data = MagicMock()
        data.name = "new-agent"
        data.model_dump.return_value = {"name": "new-agent", "display_name": "New Agent"}

        service = AIAgentService(mock_db)
        await service.create_context(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_raises(self, mock_db):
        existing = _make_context(name="existing")
        mock_db.execute.return_value = make_scalar_result(existing)

        data = MagicMock()
        data.name = "existing"

        service = AIAgentService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_context(TENANT_ACME_ID, data)


class TestDeleteContext:
    async def test_success(self, mock_db):
        context = _make_context()
        mock_db.execute.return_value = make_scalar_result(context)

        service = AIAgentService(mock_db)
        await service.delete_context(context.id)
        mock_db.delete.assert_awaited()
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = AIAgentService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.delete_context(uuid.uuid4())


class TestCreateTool:
    async def test_success(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)

        data = MagicMock()
        data.name = "new-tool"
        data.model_dump.return_value = {"name": "new-tool", "display_name": "New Tool"}
        data.webhook_headers = None

        service = AIAgentService(mock_db)
        await service.create_tool(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_raises(self, mock_db):
        existing = _make_tool(name="existing-tool")
        mock_db.execute.return_value = make_scalar_result(existing)

        data = MagicMock()
        data.name = "existing-tool"

        service = AIAgentService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_tool(TENANT_ACME_ID, data)


class TestDeleteTool:
    async def test_success(self, mock_db):
        tool = _make_tool()
        mock_db.execute.return_value = make_scalar_result(tool)

        service = AIAgentService(mock_db)
        await service.delete_tool(tool.id)
        mock_db.delete.assert_awaited()
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = AIAgentService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.delete_tool(uuid.uuid4())
