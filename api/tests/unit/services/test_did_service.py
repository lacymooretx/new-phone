"""Tests for new_phone.services.did_service — DID CRUD + provider operations."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from new_phone.models.did import DIDProvider, DIDStatus
from new_phone.providers.base import DIDPurchaseResult, DIDSearchResult
from new_phone.schemas.did import DIDCreate, DIDUpdate
from new_phone.services.did_service import DIDService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result

# ── Helpers ──────────────────────────────────────────────────────────────


def _make_did(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        number="+15551234567",
        provider=DIDProvider.CLEARLYIP,
        provider_sid="SID123",
        status=DIDStatus.ACTIVE,
        is_active=True,
        is_emergency=False,
        sms_enabled=False,
        sms_queue_id=None,
        site_id=None,
        deactivated_at=None,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ── list_dids ────────────────────────────────────────────────────────────


class TestListDids:
    async def test_returns_active_dids(self, mock_db):
        did1 = _make_did(number="+15551111111")
        did2 = _make_did(number="+15552222222")
        mock_db.execute.return_value = make_scalars_result([did1, did2])

        service = DIDService(mock_db)
        result = await service.list_dids(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_returns_empty_list(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = DIDService(mock_db)
        result = await service.list_dids(TENANT_ACME_ID)
        assert result == []

    async def test_filters_by_site_id(self, mock_db):
        site_id = uuid.uuid4()
        mock_db.execute.return_value = make_scalars_result([_make_did()])
        service = DIDService(mock_db)
        result = await service.list_dids(TENANT_ACME_ID, site_id=site_id)
        assert len(result) == 1


# ── get_did ──────────────────────────────────────────────────────────────


class TestGetDid:
    async def test_found(self, mock_db):
        did = _make_did()
        mock_db.execute.return_value = make_scalar_result(did)
        service = DIDService(mock_db)
        result = await service.get_did(TENANT_ACME_ID, did.id)
        assert result is did

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = DIDService(mock_db)
        result = await service.get_did(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


# ── create_did ───────────────────────────────────────────────────────────


class TestCreateDid:
    async def test_success(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = DIDCreate(number="+15559999999", provider=DIDProvider.CLEARLYIP)

        service = DIDService(mock_db)
        await service.create_did(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    async def test_duplicate_number_raises(self, mock_db):
        existing = _make_did(number="+15559999999")
        mock_db.execute.return_value = make_scalar_result(existing)
        data = DIDCreate(number="+15559999999", provider=DIDProvider.CLEARLYIP)

        service = DIDService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_did(TENANT_ACME_ID, data)


# ── update_did ───────────────────────────────────────────────────────────


class TestUpdateDid:
    async def test_success(self, mock_db):
        did = _make_did()
        mock_db.execute.return_value = make_scalar_result(did)
        data = DIDUpdate(sms_enabled=True)

        service = DIDService(mock_db)
        await service.update_did(TENANT_ACME_ID, did.id, data)
        mock_db.commit.assert_awaited_once()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = DIDUpdate(sms_enabled=True)

        service = DIDService(mock_db)
        with pytest.raises(ValueError, match="DID not found"):
            await service.update_did(TENANT_ACME_ID, uuid.uuid4(), data)


# ── deactivate_did ───────────────────────────────────────────────────────


class TestDeactivateDid:
    async def test_success(self, mock_db):
        did = _make_did()
        mock_db.execute.return_value = make_scalar_result(did)

        service = DIDService(mock_db)
        await service.deactivate_did(TENANT_ACME_ID, did.id)
        assert did.is_active is False
        assert did.deactivated_at is not None
        mock_db.commit.assert_awaited_once()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = DIDService(mock_db)
        with pytest.raises(ValueError, match="DID not found"):
            await service.deactivate_did(TENANT_ACME_ID, uuid.uuid4())


# ── search_available ─────────────────────────────────────────────────────


class TestSearchAvailable:
    @patch("new_phone.services.did_service.get_tenant_provider")
    async def test_uses_tenant_provider(self, mock_get_provider, mock_db):
        mock_provider = AsyncMock()
        mock_provider.search_dids.return_value = [
            DIDSearchResult(
                number="+15551112222",
                monthly_cost=1.0,
                setup_cost=0.0,
                provider="clearlyip",
                capabilities={},
            )
        ]
        mock_get_provider.return_value = mock_provider

        service = DIDService(mock_db)
        results = await service.search_available(TENANT_ACME_ID, area_code="555")
        assert len(results) == 1
        assert results[0].number == "+15551112222"

    @patch("new_phone.services.did_service.get_provider")
    async def test_uses_explicit_provider_type(self, mock_get_provider, mock_db):
        mock_provider = AsyncMock()
        mock_provider.search_dids.return_value = []
        mock_get_provider.return_value = mock_provider

        service = DIDService(mock_db)
        results = await service.search_available(
            TENANT_ACME_ID, provider_type="twilio"
        )
        assert results == []
        mock_get_provider.assert_called_once_with("twilio")


# ── purchase ─────────────────────────────────────────────────────────────


class TestPurchase:
    @patch("new_phone.services.did_service.get_provider")
    async def test_success(self, mock_get_provider, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)  # no existing DID
        mock_provider = AsyncMock()
        mock_provider.purchase_did.return_value = DIDPurchaseResult(
            number="+15553334444",
            provider_sid="PROV_SID_1",
            provider="clearlyip",
        )
        mock_get_provider.return_value = mock_provider

        service = DIDService(mock_db)
        await service.purchase(TENANT_ACME_ID, "+15553334444", "clearlyip")
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    @patch("new_phone.services.did_service.get_provider")
    async def test_duplicate_raises(self, mock_get_provider, mock_db):
        mock_db.execute.return_value = make_scalar_result(_make_did())
        service = DIDService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.purchase(TENANT_ACME_ID, "+15551234567", "clearlyip")


# ── release ──────────────────────────────────────────────────────────────


class TestRelease:
    @patch("new_phone.services.did_service.get_provider")
    async def test_success(self, mock_get_provider, mock_db):
        did = _make_did(status=DIDStatus.ACTIVE, provider=DIDProvider.CLEARLYIP)
        mock_db.execute.return_value = make_scalar_result(did)
        mock_provider = AsyncMock()
        mock_provider.release_did.return_value = True
        mock_get_provider.return_value = mock_provider

        service = DIDService(mock_db)
        await service.release(TENANT_ACME_ID, did.id)
        assert did.status == DIDStatus.RELEASED
        assert did.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = DIDService(mock_db)
        with pytest.raises(ValueError, match="DID not found"):
            await service.release(TENANT_ACME_ID, uuid.uuid4())

    async def test_already_released_raises(self, mock_db):
        did = _make_did(status=DIDStatus.RELEASED)
        mock_db.execute.return_value = make_scalar_result(did)
        service = DIDService(mock_db)
        with pytest.raises(ValueError, match="already released"):
            await service.release(TENANT_ACME_ID, did.id)

    @patch("new_phone.services.did_service.get_provider")
    async def test_provider_failure_raises(self, mock_get_provider, mock_db):
        did = _make_did(status=DIDStatus.ACTIVE, provider=DIDProvider.CLEARLYIP)
        mock_db.execute.return_value = make_scalar_result(did)
        mock_provider = AsyncMock()
        mock_provider.release_did.return_value = False
        mock_get_provider.return_value = mock_provider

        service = DIDService(mock_db)
        with pytest.raises(ValueError, match="Failed to release"):
            await service.release(TENANT_ACME_ID, did.id)


# ── configure_routing ────────────────────────────────────────────────────


class TestConfigureRouting:
    @patch("new_phone.services.did_service.get_provider")
    async def test_success(self, mock_get_provider, mock_db):
        did = _make_did(is_active=True, provider=DIDProvider.CLEARLYIP)
        mock_db.execute.return_value = make_scalar_result(did)
        mock_provider = AsyncMock()
        mock_provider.configure_did.return_value = True
        mock_get_provider.return_value = mock_provider

        service = DIDService(mock_db)
        await service.configure_routing(
            TENANT_ACME_ID, did.id, "extension", str(uuid.uuid4())
        )
        mock_db.commit.assert_awaited_once()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = DIDService(mock_db)
        with pytest.raises(ValueError, match="DID not found"):
            await service.configure_routing(
                TENANT_ACME_ID, uuid.uuid4(), "extension", str(uuid.uuid4())
            )

    async def test_inactive_did_raises(self, mock_db):
        did = _make_did(is_active=False)
        mock_db.execute.return_value = make_scalar_result(did)
        service = DIDService(mock_db)
        with pytest.raises(ValueError, match="inactive DID"):
            await service.configure_routing(
                TENANT_ACME_ID, did.id, "extension", str(uuid.uuid4())
            )
