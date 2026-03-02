"""Tests for new_phone.services.audio_prompt_service — audio prompt CRUD."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from new_phone.services.audio_prompt_service import AudioPromptService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_prompt(**overrides):
    prompt = MagicMock()
    prompt.id = overrides.get("id", uuid.uuid4())
    prompt.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    prompt.name = overrides.get("name", "Welcome Greeting")
    prompt.category = overrides.get("category", "greeting")
    prompt.storage_path = overrides.get("storage_path", "prompts/acme/test.wav")
    prompt.is_active = overrides.get("is_active", True)
    return prompt


class TestListPrompts:
    async def test_returns_list(self, mock_db):
        p1 = _make_prompt(name="Welcome")
        p2 = _make_prompt(name="Hold Music")
        mock_db.execute.return_value = make_scalars_result([p1, p2])

        service = AudioPromptService(mock_db)
        result = await service.list_prompts(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = AudioPromptService(mock_db)
        result = await service.list_prompts(TENANT_ACME_ID)
        assert result == []


class TestGetPrompt:
    async def test_found(self, mock_db):
        prompt = _make_prompt(name="Welcome")
        mock_db.execute.return_value = make_scalar_result(prompt)
        service = AudioPromptService(mock_db)
        result = await service.get_prompt(TENANT_ACME_ID, prompt.id)
        assert result.name == "Welcome"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = AudioPromptService(mock_db)
        result = await service.get_prompt(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreatePrompt:
    @patch("new_phone.services.audio_prompt_service.os.makedirs")
    @patch("builtins.open", new_callable=MagicMock)
    async def test_success(self, mock_open, mock_makedirs, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)  # no duplicate

        storage = MagicMock()
        storage.upload_bytes.return_value = True

        service = AudioPromptService(mock_db, storage=storage)
        await service.create_prompt(
            tenant_id=TENANT_ACME_ID,
            tenant_slug="acme",
            name="New Prompt",
            category="greeting",
            description="A new greeting",
            file_data=b"RIFF" + b"\x00" * 100,
            filename="greeting.wav",
        )
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_name_raises(self, mock_db):
        existing = _make_prompt(name="Welcome")
        mock_db.execute.return_value = make_scalar_result(existing)

        service = AudioPromptService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_prompt(
                tenant_id=TENANT_ACME_ID,
                tenant_slug="acme",
                name="Welcome",
                category="greeting",
                description=None,
                file_data=b"data",
                filename="welcome.wav",
            )


class TestSoftDelete:
    async def test_success(self, mock_db):
        prompt = _make_prompt(is_active=True)
        mock_db.execute.return_value = make_scalar_result(prompt)
        service = AudioPromptService(mock_db)
        result = await service.soft_delete(TENANT_ACME_ID, prompt.id)
        assert result.is_active is False

    async def test_not_found_returns_none(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = AudioPromptService(mock_db)
        result = await service.soft_delete(TENANT_ACME_ID, uuid.uuid4())
        assert result is None
