"""Tests for new_phone.services.sip_trunk_service — SIP trunk CRUD + provisioning."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from new_phone.models.sip_trunk import TrunkAuthType, TrunkTransport
from new_phone.providers.base import TrunkProvisionResult, TrunkTestResult
from new_phone.schemas.sip_trunk import SIPTrunkCreate, SIPTrunkUpdate
from new_phone.services.sip_trunk_service import SIPTrunkService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_trunk(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        name="Primary Trunk",
        auth_type=TrunkAuthType.REGISTRATION,
        host="sip.example.com",
        port=5061,
        username="trunkuser",
        encrypted_password="encrypted_pw",
        ip_acl=None,
        codec_preferences=None,
        max_channels=30,
        transport=TrunkTransport.TLS,
        inbound_cid_mode="passthrough",
        failover_trunk_id=None,
        notes=None,
        is_active=True,
        provider_type="clearlyip",
        provider_trunk_id="PROV_TRUNK_1",
        deactivated_at=None,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListTrunks:
    async def test_returns_active_trunks(self, mock_db):
        t1 = _make_trunk(name="Trunk A")
        t2 = _make_trunk(name="Trunk B")
        mock_db.execute.return_value = make_scalars_result([t1, t2])

        service = SIPTrunkService(mock_db)
        result = await service.list_trunks(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty_list(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = SIPTrunkService(mock_db)
        result = await service.list_trunks(TENANT_ACME_ID)
        assert result == []


class TestGetTrunk:
    async def test_found(self, mock_db):
        trunk = _make_trunk()
        mock_db.execute.return_value = make_scalar_result(trunk)
        service = SIPTrunkService(mock_db)
        result = await service.get_trunk(TENANT_ACME_ID, trunk.id)
        assert result is trunk

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SIPTrunkService(mock_db)
        result = await service.get_trunk(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateTrunk:
    async def test_success_with_password(self, mock_db):
        data = SIPTrunkCreate(
            name="New Trunk",
            auth_type=TrunkAuthType.REGISTRATION,
            host="sip.new.com",
            password="secret123",
        )
        service = SIPTrunkService(mock_db)
        await service.create_trunk(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.encrypted_password is not None
        mock_db.commit.assert_awaited_once()

    async def test_success_without_password(self, mock_db):
        data = SIPTrunkCreate(
            name="IP Auth Trunk",
            auth_type=TrunkAuthType.IP_AUTH,
            host="sip.ipauth.com",
        )
        service = SIPTrunkService(mock_db)
        await service.create_trunk(TENANT_ACME_ID, data)
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.encrypted_password is None


class TestUpdateTrunk:
    async def test_success(self, mock_db):
        trunk = _make_trunk()
        mock_db.execute.return_value = make_scalar_result(trunk)
        data = SIPTrunkUpdate(name="Updated Trunk")

        service = SIPTrunkService(mock_db)
        await service.update_trunk(TENANT_ACME_ID, trunk.id, data)
        assert trunk.name == "Updated Trunk"
        mock_db.commit.assert_awaited_once()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = SIPTrunkUpdate(name="Updated")
        service = SIPTrunkService(mock_db)
        with pytest.raises(ValueError, match="SIP trunk not found"):
            await service.update_trunk(TENANT_ACME_ID, uuid.uuid4(), data)

    async def test_password_update_encrypts(self, mock_db):
        trunk = _make_trunk()
        mock_db.execute.return_value = make_scalar_result(trunk)
        data = SIPTrunkUpdate(password="newpassword")

        service = SIPTrunkService(mock_db)
        await service.update_trunk(TENANT_ACME_ID, trunk.id, data)
        assert trunk.encrypted_password is not None
        assert trunk.encrypted_password != "newpassword"


class TestDeactivateTrunk:
    async def test_success(self, mock_db):
        trunk = _make_trunk()
        mock_db.execute.return_value = make_scalar_result(trunk)

        service = SIPTrunkService(mock_db)
        await service.deactivate_trunk(TENANT_ACME_ID, trunk.id)
        assert trunk.is_active is False
        assert trunk.deactivated_at is not None

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SIPTrunkService(mock_db)
        with pytest.raises(ValueError, match="SIP trunk not found"):
            await service.deactivate_trunk(TENANT_ACME_ID, uuid.uuid4())


class TestProvision:
    @patch("new_phone.services.sip_trunk_service.get_provider")
    async def test_success(self, mock_get_provider, mock_db):
        mock_provider = AsyncMock()
        mock_provider.create_trunk.return_value = TrunkProvisionResult(
            provider_trunk_id="PROV_123",
            host="sip.provider.com",
            port=5061,
            username="provuser",
            password="provpass",
        )
        mock_get_provider.return_value = mock_provider

        service = SIPTrunkService(mock_db)
        await service.provision(
            TENANT_ACME_ID, "clearlyip", "test-trunk"
        )
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()


class TestDeprovision:
    @patch("new_phone.services.sip_trunk_service.get_provider")
    async def test_success(self, mock_get_provider, mock_db):
        trunk = _make_trunk()
        mock_db.execute.return_value = make_scalar_result(trunk)
        mock_provider = AsyncMock()
        mock_provider.delete_trunk.return_value = True
        mock_get_provider.return_value = mock_provider

        service = SIPTrunkService(mock_db)
        await service.deprovision(TENANT_ACME_ID, trunk.id)
        assert trunk.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SIPTrunkService(mock_db)
        with pytest.raises(ValueError, match="SIP trunk not found"):
            await service.deprovision(TENANT_ACME_ID, uuid.uuid4())

    @patch("new_phone.services.sip_trunk_service.get_provider")
    async def test_provider_failure_raises(self, mock_get_provider, mock_db):
        trunk = _make_trunk()
        mock_db.execute.return_value = make_scalar_result(trunk)
        mock_provider = AsyncMock()
        mock_provider.delete_trunk.return_value = False
        mock_get_provider.return_value = mock_provider

        service = SIPTrunkService(mock_db)
        with pytest.raises(ValueError, match="Failed to delete"):
            await service.deprovision(TENANT_ACME_ID, trunk.id)


class TestTestTrunk:
    @patch("new_phone.services.sip_trunk_service.get_provider")
    async def test_provider_managed(self, mock_get_provider, mock_db):
        trunk = _make_trunk()
        mock_db.execute.return_value = make_scalar_result(trunk)
        mock_provider = AsyncMock()
        mock_provider.test_trunk.return_value = TrunkTestResult(
            status="ok", latency_ms=42.0, error=None
        )
        mock_get_provider.return_value = mock_provider

        service = SIPTrunkService(mock_db)
        result = await service.test_trunk(TENANT_ACME_ID, trunk.id)
        assert result.status == "ok"
        assert result.latency_ms == 42.0

    async def test_non_provider_managed_skipped(self, mock_db):
        trunk = _make_trunk(provider_trunk_id=None, provider_type=None)
        mock_db.execute.return_value = make_scalar_result(trunk)

        service = SIPTrunkService(mock_db)
        result = await service.test_trunk(TENANT_ACME_ID, trunk.id)
        assert result.status == "skipped"

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SIPTrunkService(mock_db)
        with pytest.raises(ValueError, match="SIP trunk not found"):
            await service.test_trunk(TENANT_ACME_ID, uuid.uuid4())
