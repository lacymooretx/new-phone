"""Tests for new_phone.services.building_webhook_service — building webhook CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.building_webhook_service import BuildingWebhookService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_webhook(**overrides):
    wh = MagicMock()
    wh.id = overrides.get("id", uuid.uuid4())
    wh.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    wh.name = overrides.get("name", "Front Door")
    wh.description = overrides.get("description", "Main entrance")
    wh.secret_token = overrides.get("secret_token", "test-token-abc123")
    wh.is_active = overrides.get("is_active", True)
    wh.actions = overrides.get("actions", [])
    return wh


class TestListWebhooks:
    async def test_returns_list(self, mock_db):
        w1 = _make_webhook(name="Front Door")
        w2 = _make_webhook(name="Loading Dock")
        mock_db.execute.return_value = make_scalars_result([w1, w2])

        service = BuildingWebhookService(mock_db)
        result = await service.list_webhooks(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = BuildingWebhookService(mock_db)
        result = await service.list_webhooks(TENANT_ACME_ID)
        assert result == []


class TestGetWebhook:
    async def test_found(self, mock_db):
        wh = _make_webhook(name="Front Door")
        mock_db.execute.return_value = make_scalar_result(wh)
        service = BuildingWebhookService(mock_db)
        result = await service.get_webhook(TENANT_ACME_ID, wh.id)
        assert result.name == "Front Door"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = BuildingWebhookService(mock_db)
        result = await service.get_webhook(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateWebhook:
    async def test_success(self, mock_db):
        from new_phone.schemas.building_webhook import BuildingWebhookCreate

        service = BuildingWebhookService(mock_db)
        data = BuildingWebhookCreate(name="New Webhook", description="Test")
        await service.create_webhook(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()


class TestUpdateWebhook:
    async def test_success(self, mock_db):
        from new_phone.schemas.building_webhook import BuildingWebhookUpdate

        wh = _make_webhook()
        mock_db.execute.return_value = make_scalar_result(wh)
        service = BuildingWebhookService(mock_db)
        data = BuildingWebhookUpdate(name="Updated Webhook")
        await service.update_webhook(TENANT_ACME_ID, wh.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.building_webhook import BuildingWebhookUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = BuildingWebhookService(mock_db)
        data = BuildingWebhookUpdate(name="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_webhook(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateWebhook:
    async def test_success(self, mock_db):
        wh = _make_webhook(is_active=True)
        mock_db.execute.return_value = make_scalar_result(wh)
        service = BuildingWebhookService(mock_db)
        await service.deactivate_webhook(TENANT_ACME_ID, wh.id)
        assert wh.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = BuildingWebhookService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_webhook(TENANT_ACME_ID, uuid.uuid4())


class TestAddAction:
    async def test_success(self, mock_db):
        from new_phone.models.building_webhook import WebhookActionType
        from new_phone.schemas.building_webhook import BuildingWebhookActionCreate

        wh = _make_webhook()
        mock_db.execute.return_value = make_scalar_result(wh)
        service = BuildingWebhookService(mock_db)
        data = BuildingWebhookActionCreate(
            event_type_match="door_open",
            action_type=WebhookActionType.NOTIFICATION,
            action_config={"message": "Door opened"},
        )
        await service.add_action(TENANT_ACME_ID, wh.id, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_webhook_not_found_raises(self, mock_db):
        from new_phone.models.building_webhook import WebhookActionType
        from new_phone.schemas.building_webhook import BuildingWebhookActionCreate

        mock_db.execute.return_value = make_scalar_result(None)
        service = BuildingWebhookService(mock_db)
        data = BuildingWebhookActionCreate(
            event_type_match="door_open",
            action_type=WebhookActionType.NOTIFICATION,
            action_config={},
        )
        with pytest.raises(ValueError, match="not found"):
            await service.add_action(TENANT_ACME_ID, uuid.uuid4(), data)


class TestRemoveAction:
    async def test_success(self, mock_db):
        action = MagicMock()
        action.id = uuid.uuid4()
        mock_db.execute.return_value = make_scalar_result(action)
        service = BuildingWebhookService(mock_db)
        await service.remove_action(TENANT_ACME_ID, action.id)
        mock_db.delete.assert_awaited_once_with(action)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = BuildingWebhookService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.remove_action(TENANT_ACME_ID, uuid.uuid4())


class TestVerifySignature:
    def test_valid_signature(self):
        import hashlib
        import hmac

        token = "my-secret"
        payload = b'{"event":"door_open"}'
        sig = hmac.new(token.encode(), payload, hashlib.sha256).hexdigest()

        assert BuildingWebhookService.verify_signature(token, payload, sig) is True

    def test_invalid_signature(self):
        assert BuildingWebhookService.verify_signature("token", b"data", "badsig") is False
