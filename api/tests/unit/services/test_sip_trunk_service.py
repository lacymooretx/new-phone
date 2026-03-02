"""Tests for new_phone.services.sip_trunk_service — SIP trunk CRUD + encryption."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.sip_trunk_service import SIPTrunkService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_trunk(**overrides):
    trunk = MagicMock()
    trunk.id = overrides.get("id", uuid.uuid4())
    trunk.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    trunk.name = overrides.get("name", "Primary Trunk")
    trunk.is_active = overrides.get("is_active", True)
    trunk.encrypted_password = overrides.get("encrypted_password")
    trunk.deactivated_at = overrides.get("deactivated_at")
    return trunk


class TestListTrunks:
    async def test_returns_list(self, mock_db):
        t1 = _make_trunk(name="Primary")
        t2 = _make_trunk(name="Backup")
        mock_db.execute.return_value = make_scalars_result([t1, t2])

        service = SIPTrunkService(mock_db)
        result = await service.list_trunks(TENANT_ACME_ID)
        assert len(result) == 2


class TestGetTrunk:
    async def test_found(self, mock_db):
        trunk = _make_trunk(name="Primary")
        mock_db.execute.return_value = make_scalar_result(trunk)
        service = SIPTrunkService(mock_db)
        result = await service.get_trunk(TENANT_ACME_ID, trunk.id)
        assert result.name == "Primary"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SIPTrunkService(mock_db)
        result = await service.get_trunk(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateTrunk:
    async def test_success_with_password(self, mock_db):
        from new_phone.schemas.sip_trunk import SIPTrunkCreate

        service = SIPTrunkService(mock_db)
        data = SIPTrunkCreate(
            name="New Trunk",
            auth_type="registration",
            host="sip.provider.com",
            port=5061,
            transport="tls",
            username="user",
            password="secret-pw",
        )
        await service.create_trunk(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert added.name == "New Trunk"
        # Password should be encrypted
        assert added.encrypted_password is not None
        assert added.encrypted_password != "secret-pw"

    async def test_success_without_password(self, mock_db):
        from new_phone.schemas.sip_trunk import SIPTrunkCreate

        service = SIPTrunkService(mock_db)
        data = SIPTrunkCreate(
            name="IP Auth Trunk",
            auth_type="ip_auth",
            host="sip.provider.com",
            port=5061,
            transport="tls",
        )
        await service.create_trunk(TENANT_ACME_ID, data)
        added = mock_db.add.call_args[0][0]
        assert added.encrypted_password is None


class TestUpdateTrunk:
    async def test_success(self, mock_db):
        from new_phone.schemas.sip_trunk import SIPTrunkUpdate

        trunk = _make_trunk(name="Old")
        mock_db.execute.return_value = make_scalar_result(trunk)
        service = SIPTrunkService(mock_db)
        data = SIPTrunkUpdate(name="Updated")
        await service.update_trunk(TENANT_ACME_ID, trunk.id, data)
        mock_db.commit.assert_awaited()

    async def test_password_update_encrypts(self, mock_db):
        from new_phone.schemas.sip_trunk import SIPTrunkUpdate

        trunk = _make_trunk()
        mock_db.execute.return_value = make_scalar_result(trunk)
        service = SIPTrunkService(mock_db)
        data = SIPTrunkUpdate(password="new-secret")
        await service.update_trunk(TENANT_ACME_ID, trunk.id, data)
        assert trunk.encrypted_password is not None
        assert trunk.encrypted_password != "new-secret"

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.sip_trunk import SIPTrunkUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = SIPTrunkService(mock_db)
        data = SIPTrunkUpdate(name="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_trunk(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateTrunk:
    async def test_success(self, mock_db):
        trunk = _make_trunk(is_active=True)
        mock_db.execute.return_value = make_scalar_result(trunk)
        service = SIPTrunkService(mock_db)
        await service.deactivate_trunk(TENANT_ACME_ID, trunk.id)
        assert trunk.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SIPTrunkService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_trunk(TENANT_ACME_ID, uuid.uuid4())
