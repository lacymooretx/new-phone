"""Tests for new_phone.services.silent_intercom_service — silent intercom session CRUD."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from new_phone.services.silent_intercom_service import SilentIntercomService
from tests.unit.conftest import (
    TENANT_ACME_ID,
    USER_ACME_ADMIN_ID,
    make_scalar_result,
    make_scalars_result,
)


def _make_session(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        initiated_by_user_id=USER_ACME_ADMIN_ID,
        target_extension_id=uuid.uuid4(),
        status="active",
        max_duration_seconds=300,
        fs_uuid=None,
        ended_at=None,
        ended_by_user_id=None,
        started_at=None,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_security_config(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        silent_intercom_enabled=True,
        silent_intercom_max_seconds=300,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_extension(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        extension_number="100",
        sip_username="sip-100",
        is_active=True,
        user_id=USER_ACME_ADMIN_ID,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListSessions:
    async def test_returns_list(self, mock_db):
        s1 = _make_session()
        s2 = _make_session()
        mock_db.execute.return_value = make_scalars_result([s1, s2])

        service = SilentIntercomService(mock_db)
        result = await service.list_sessions(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_returns_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = SilentIntercomService(mock_db)
        result = await service.list_sessions(TENANT_ACME_ID)
        assert result == []


class TestGetSession:
    async def test_found(self, mock_db):
        session = _make_session()
        mock_db.execute.return_value = make_scalar_result(session)

        service = SilentIntercomService(mock_db)
        result = await service.get_session(TENANT_ACME_ID, session.id)
        assert result.id == session.id

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SilentIntercomService(mock_db)
        result = await service.get_session(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestStartSession:
    async def test_success(self, mock_db):
        config = _make_security_config(silent_intercom_enabled=True)
        target_ext = _make_extension()
        data = MagicMock()
        data.target_extension_id = target_ext.id

        # 1st execute: security config, 2nd: target extension
        mock_db.execute.side_effect = [
            make_scalar_result(config),
            make_scalar_result(target_ext),
        ]

        service = SilentIntercomService(mock_db)
        with patch("new_phone.services.silent_intercom_service.set_tenant_context", new_callable=AsyncMock):
            await service.start_session(TENANT_ACME_ID, USER_ACME_ADMIN_ID, data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_not_enabled_raises(self, mock_db):
        config = _make_security_config(silent_intercom_enabled=False)
        data = MagicMock()
        data.target_extension_id = uuid.uuid4()

        mock_db.execute.return_value = make_scalar_result(config)

        service = SilentIntercomService(mock_db)
        with (
            patch("new_phone.services.silent_intercom_service.set_tenant_context", new_callable=AsyncMock),
            pytest.raises(ValueError, match="not enabled"),
        ):
            await service.start_session(TENANT_ACME_ID, USER_ACME_ADMIN_ID, data)

    async def test_target_extension_not_found_raises(self, mock_db):
        config = _make_security_config(silent_intercom_enabled=True)
        data = MagicMock()
        data.target_extension_id = uuid.uuid4()

        mock_db.execute.side_effect = [
            make_scalar_result(config),
            make_scalar_result(None),
        ]

        service = SilentIntercomService(mock_db)
        with (
            patch("new_phone.services.silent_intercom_service.set_tenant_context", new_callable=AsyncMock),
            pytest.raises(ValueError, match="Target extension not found"),
        ):
            await service.start_session(TENANT_ACME_ID, USER_ACME_ADMIN_ID, data)


class TestEndSession:
    async def test_success(self, mock_db):
        session = _make_session(status="active", fs_uuid=None)
        # get_session calls execute once
        mock_db.execute.return_value = make_scalar_result(session)

        service = SilentIntercomService(mock_db)
        with patch("new_phone.services.silent_intercom_service.set_tenant_context", new_callable=AsyncMock):
            # Use the same session.status attribute check
            session.status = "active"
            # Mock SessionStatus enum comparison
            with patch("new_phone.services.silent_intercom_service.SessionStatus") as mock_status:
                mock_status.ACTIVE = "active"
                mock_status.ENDED_MANUAL = "ended_manual"
                result = await service.end_session(TENANT_ACME_ID, session.id, USER_ACME_ADMIN_ID)

        assert result.status == "ended_manual"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)

        service = SilentIntercomService(mock_db)
        with (
            patch("new_phone.services.silent_intercom_service.set_tenant_context", new_callable=AsyncMock),
            pytest.raises(ValueError, match="not found"),
        ):
            await service.end_session(TENANT_ACME_ID, uuid.uuid4(), USER_ACME_ADMIN_ID)
