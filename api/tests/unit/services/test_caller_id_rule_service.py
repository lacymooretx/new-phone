"""Tests for new_phone.services.caller_id_rule_service — caller ID rule CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.caller_id_rule_service import CallerIdRuleService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_rule(**overrides):
    rule = MagicMock()
    rule.id = overrides.get("id", uuid.uuid4())
    rule.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    rule.name = overrides.get("name", "Block Spam")
    rule.rule_type = overrides.get("rule_type", "block")
    rule.match_pattern = overrides.get("match_pattern", "+15551234567")
    rule.action = overrides.get("action", "reject")
    rule.priority = overrides.get("priority", 0)
    rule.is_active = overrides.get("is_active", True)
    return rule


class TestListCallerIdRules:
    async def test_returns_list(self, mock_db):
        r1 = _make_rule(name="Block Spam")
        r2 = _make_rule(name="Allow VIP")
        mock_db.execute.return_value = make_scalars_result([r1, r2])

        service = CallerIdRuleService(mock_db)
        result = await service.list_rules(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = CallerIdRuleService(mock_db)
        result = await service.list_rules(TENANT_ACME_ID)
        assert result == []


class TestGetCallerIdRule:
    async def test_found(self, mock_db):
        rule = _make_rule(name="Block Spam")
        mock_db.execute.return_value = make_scalar_result(rule)
        service = CallerIdRuleService(mock_db)
        result = await service.get_rule(TENANT_ACME_ID, rule.id)
        assert result.name == "Block Spam"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = CallerIdRuleService(mock_db)
        result = await service.get_rule(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateCallerIdRule:
    async def test_success(self, mock_db):
        from new_phone.models.caller_id_rule import RuleAction, RuleType
        from new_phone.schemas.caller_id_rule import CallerIdRuleCreate

        mock_db.execute.return_value = make_scalar_result(None)  # no duplicate

        service = CallerIdRuleService(mock_db)
        data = CallerIdRuleCreate(
            name="New Rule",
            rule_type=RuleType.BLOCK,
            match_pattern="+15551234567",
            action=RuleAction.REJECT,
        )
        await service.create_rule(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_duplicate_name_raises(self, mock_db):
        from new_phone.models.caller_id_rule import RuleAction, RuleType
        from new_phone.schemas.caller_id_rule import CallerIdRuleCreate

        existing = _make_rule(name="Block Spam")
        mock_db.execute.return_value = make_scalar_result(existing)

        service = CallerIdRuleService(mock_db)
        data = CallerIdRuleCreate(
            name="Block Spam",
            rule_type=RuleType.BLOCK,
            match_pattern="+15559876543",
            action=RuleAction.REJECT,
        )
        with pytest.raises(ValueError, match="already exists"):
            await service.create_rule(TENANT_ACME_ID, data)


class TestUpdateCallerIdRule:
    async def test_success(self, mock_db):
        from new_phone.schemas.caller_id_rule import CallerIdRuleUpdate

        rule = _make_rule()
        mock_db.execute.return_value = make_scalar_result(rule)
        service = CallerIdRuleService(mock_db)
        data = CallerIdRuleUpdate(name="Updated Rule")
        await service.update_rule(TENANT_ACME_ID, rule.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.caller_id_rule import CallerIdRuleUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = CallerIdRuleService(mock_db)
        data = CallerIdRuleUpdate(name="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_rule(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateCallerIdRule:
    async def test_success(self, mock_db):
        rule = _make_rule(is_active=True)
        mock_db.execute.return_value = make_scalar_result(rule)
        service = CallerIdRuleService(mock_db)
        await service.deactivate(TENANT_ACME_ID, rule.id)
        assert rule.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = CallerIdRuleService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate(TENANT_ACME_ID, uuid.uuid4())
