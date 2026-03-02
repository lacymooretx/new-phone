"""Tests for new_phone.services.compliance_monitoring_service — compliance rule CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.compliance_monitoring_service import ComplianceMonitoringService
from tests.unit.conftest import (
    TENANT_ACME_ID,
    USER_ACME_ADMIN_ID,
    make_scalar_result,
    make_scalars_result,
)


def _make_rule(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        name="Greeting Required",
        category="quality",
        scope_type="queue",
        is_active=True,
        severity="medium",
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_evaluation(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        cdr_id=uuid.uuid4(),
        overall_score=85.0,
        is_flagged=False,
        status="completed",
        reviewed_by_id=None,
        reviewed_at=None,
        review_notes=None,
        created_at=None,
        evaluated_at=None,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListRules:
    async def test_returns_list(self, mock_db):
        r1 = _make_rule(name="Rule A")
        r2 = _make_rule(name="Rule B")
        mock_db.execute.return_value = make_scalars_result([r1, r2])

        service = ComplianceMonitoringService(mock_db)
        result = await service.list_rules(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_returns_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = ComplianceMonitoringService(mock_db)
        result = await service.list_rules(TENANT_ACME_ID)
        assert result == []


class TestGetRule:
    async def test_found(self, mock_db):
        rule = _make_rule()
        mock_db.execute.return_value = make_scalar_result(rule)

        service = ComplianceMonitoringService(mock_db)
        result = await service.get_rule(TENANT_ACME_ID, rule.id)
        assert result.name == "Greeting Required"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ComplianceMonitoringService(mock_db)
        result = await service.get_rule(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateRule:
    async def test_success(self, mock_db):
        # Duplicate check returns None, then flush/refresh
        mock_db.execute.return_value = make_scalar_result(None)

        data = {"name": "New Rule", "category": "quality", "scope_type": "queue", "severity": "high"}

        service = ComplianceMonitoringService(mock_db)
        await service.create_rule(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited()

    async def test_duplicate_name_raises(self, mock_db):
        existing = _make_rule(name="Existing Rule")
        mock_db.execute.return_value = make_scalar_result(existing)

        data = {"name": "Existing Rule"}
        service = ComplianceMonitoringService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_rule(TENANT_ACME_ID, data)


class TestUpdateRule:
    async def test_success(self, mock_db):
        rule = _make_rule(name="Old Name")
        # set_tenant_context, set_tenant_context (in get_rule), get_rule query, duplicate name check
        mock_db.execute.side_effect = [
            MagicMock(),  # set_tenant_context in update_rule
            MagicMock(),  # set_tenant_context in get_rule
            make_scalar_result(rule),
            make_scalar_result(None),
        ]

        data = {"name": "New Name"}
        service = ComplianceMonitoringService(mock_db)
        result = await service.update_rule(TENANT_ACME_ID, rule.id, data)
        assert result is not None
        mock_db.flush.assert_awaited()

    async def test_not_found_returns_none(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)

        service = ComplianceMonitoringService(mock_db)
        result = await service.update_rule(TENANT_ACME_ID, uuid.uuid4(), {"name": "X"})
        assert result is None


class TestDeactivateRule:
    async def test_success(self, mock_db):
        rule = _make_rule(is_active=True)
        mock_db.execute.return_value = make_scalar_result(rule)

        service = ComplianceMonitoringService(mock_db)
        result = await service.deactivate_rule(TENANT_ACME_ID, rule.id)
        assert result is True
        assert rule.is_active is False

    async def test_not_found_returns_false(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ComplianceMonitoringService(mock_db)
        result = await service.deactivate_rule(TENANT_ACME_ID, uuid.uuid4())
        assert result is False


class TestListEvaluations:
    async def test_returns_list(self, mock_db):
        e1 = _make_evaluation()
        e2 = _make_evaluation()
        mock_db.execute.return_value = make_scalars_result([e1, e2])

        service = ComplianceMonitoringService(mock_db)
        result = await service.list_evaluations(TENANT_ACME_ID)
        assert len(result) == 2


class TestReviewEvaluation:
    async def test_success(self, mock_db):
        evaluation = _make_evaluation(status="completed")
        mock_db.execute.return_value = make_scalar_result(evaluation)

        service = ComplianceMonitoringService(mock_db)
        result = await service.review_evaluation(
            TENANT_ACME_ID, evaluation.id, USER_ACME_ADMIN_ID, "Looks good"
        )
        assert result is not None
        assert result.status == "reviewed"
        mock_db.flush.assert_awaited()

    async def test_not_found_returns_none(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ComplianceMonitoringService(mock_db)
        result = await service.review_evaluation(
            TENANT_ACME_ID, uuid.uuid4(), USER_ACME_ADMIN_ID, None
        )
        assert result is None
