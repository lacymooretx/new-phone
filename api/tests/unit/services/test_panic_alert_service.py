"""Tests for new_phone.services.panic_alert_service — panic alert CRUD."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from new_phone.services.panic_alert_service import PanicAlertService
from tests.unit.conftest import (
    TENANT_ACME_ID,
    USER_ACME_ADMIN_ID,
    make_scalar_result,
    make_scalars_result,
)


def _make_alert(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        triggered_by_user_id=USER_ACME_ADMIN_ID,
        triggered_from_extension_id=uuid.uuid4(),
        trigger_source="phone_button",
        alert_type="emergency",
        status="active",
        location_building="HQ",
        location_floor="2",
        location_description="Near elevator",
        acknowledged_by_user_id=None,
        acknowledged_at=None,
        resolved_by_user_id=None,
        resolved_at=None,
        resolution_notes=None,
        created_at=None,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestTriggerAlert:
    async def test_success(self, mock_db):
        data = MagicMock()
        data.extension_id = uuid.uuid4()
        data.trigger_source = "phone_button"
        data.alert_type = "emergency"
        data.location_building = "HQ"
        data.location_floor = "2"
        data.location_description = "Near elevator"

        service = PanicAlertService(mock_db)
        with (
            patch("new_phone.services.panic_alert_service.set_tenant_context", new_callable=AsyncMock),
            patch.object(service, "_dispatch_notifications", new_callable=AsyncMock),
        ):
            await service.trigger_alert(TENANT_ACME_ID, USER_ACME_ADMIN_ID, data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()


class TestGetAlert:
    async def test_found(self, mock_db):
        alert = _make_alert()
        mock_db.execute.return_value = make_scalar_result(alert)

        service = PanicAlertService(mock_db)
        result = await service.get_alert(TENANT_ACME_ID, alert.id)
        assert result.id == alert.id

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = PanicAlertService(mock_db)
        result = await service.get_alert(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestListAlerts:
    async def test_returns_list(self, mock_db):
        a1 = _make_alert()
        a2 = _make_alert()
        mock_db.execute.return_value = make_scalars_result([a1, a2])

        service = PanicAlertService(mock_db)
        result = await service.list_alerts(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_returns_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = PanicAlertService(mock_db)
        result = await service.list_alerts(TENANT_ACME_ID)
        assert result == []


class TestAcknowledge:
    async def test_success(self, mock_db):
        alert = _make_alert(status="active")
        mock_db.execute.return_value = make_scalar_result(alert)

        service = PanicAlertService(mock_db)
        with (
            patch("new_phone.services.panic_alert_service.set_tenant_context", new_callable=AsyncMock),
            patch("new_phone.services.panic_alert_service.AlertStatus") as mock_status,
        ):
            mock_status.ACTIVE = "active"
            mock_status.ACKNOWLEDGED = "acknowledged"
            result = await service.acknowledge(TENANT_ACME_ID, alert.id, USER_ACME_ADMIN_ID)

        assert result.status == "acknowledged"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = PanicAlertService(mock_db)
        with (
            patch("new_phone.services.panic_alert_service.set_tenant_context", new_callable=AsyncMock),
            pytest.raises(ValueError, match="not found"),
        ):
            await service.acknowledge(TENANT_ACME_ID, uuid.uuid4(), USER_ACME_ADMIN_ID)

    async def test_not_active_raises(self, mock_db):
        alert = _make_alert(status="resolved")
        mock_db.execute.return_value = make_scalar_result(alert)

        service = PanicAlertService(mock_db)
        with (
            patch("new_phone.services.panic_alert_service.set_tenant_context", new_callable=AsyncMock),
            patch("new_phone.services.panic_alert_service.AlertStatus") as mock_status,
        ):
            mock_status.ACTIVE = "active"
            with pytest.raises(ValueError, match="not active"):
                await service.acknowledge(TENANT_ACME_ID, alert.id, USER_ACME_ADMIN_ID)


class TestResolve:
    async def test_success(self, mock_db):
        alert = _make_alert(status="acknowledged")
        mock_db.execute.return_value = make_scalar_result(alert)

        data = MagicMock()
        data.mark_false_alarm = False
        data.resolution_notes = "All clear"

        service = PanicAlertService(mock_db)
        with (
            patch("new_phone.services.panic_alert_service.set_tenant_context", new_callable=AsyncMock),
            patch("new_phone.services.panic_alert_service.AlertStatus") as mock_status,
        ):
            mock_status.RESOLVED = "resolved"
            mock_status.FALSE_ALARM = "false_alarm"
            result = await service.resolve(TENANT_ACME_ID, alert.id, USER_ACME_ADMIN_ID, data)

        assert result.status == "resolved"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = MagicMock()
        service = PanicAlertService(mock_db)
        with (
            patch("new_phone.services.panic_alert_service.set_tenant_context", new_callable=AsyncMock),
            pytest.raises(ValueError, match="not found"),
        ):
            await service.resolve(TENANT_ACME_ID, uuid.uuid4(), USER_ACME_ADMIN_ID, data)
