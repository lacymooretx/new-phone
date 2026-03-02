"""Tests for new_phone.services.did_service — DID CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.did_service import DIDService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_did(**overrides):
    did = MagicMock()
    did.id = overrides.get("id", uuid.uuid4())
    did.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    did.number = overrides.get("number", "+15551234567")
    did.is_active = overrides.get("is_active", True)
    did.deactivated_at = overrides.get("deactivated_at")
    return did


class TestListDids:
    async def test_returns_list(self, mock_db):
        d1 = _make_did(number="+15551111111")
        d2 = _make_did(number="+15552222222")
        mock_db.execute.return_value = make_scalars_result([d1, d2])

        service = DIDService(mock_db)
        result = await service.list_dids(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = DIDService(mock_db)
        result = await service.list_dids(TENANT_ACME_ID)
        assert result == []


class TestGetDid:
    async def test_found(self, mock_db):
        did = _make_did(number="+15551234567")
        mock_db.execute.return_value = make_scalar_result(did)
        service = DIDService(mock_db)
        result = await service.get_did(TENANT_ACME_ID, did.id)
        assert result.number == "+15551234567"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = DIDService(mock_db)
        result = await service.get_did(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateDid:
    async def test_success(self, mock_db):
        from new_phone.schemas.did import DIDCreate

        mock_db.execute.return_value = make_scalar_result(None)  # no duplicate

        service = DIDService(mock_db)
        data = DIDCreate(number="+15559998888", provider="manual")
        await service.create_did(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert added.number == "+15559998888"

    async def test_duplicate_number_raises(self, mock_db):
        from new_phone.schemas.did import DIDCreate

        existing = _make_did(number="+15551234567")
        mock_db.execute.return_value = make_scalar_result(existing)

        service = DIDService(mock_db)
        data = DIDCreate(number="+15551234567", provider="manual")
        with pytest.raises(ValueError, match="already exists"):
            await service.create_did(TENANT_ACME_ID, data)


class TestUpdateDid:
    async def test_success(self, mock_db):
        from new_phone.schemas.did import DIDUpdate

        did = _make_did()
        mock_db.execute.return_value = make_scalar_result(did)
        service = DIDService(mock_db)
        data = DIDUpdate(description="Updated")
        await service.update_did(TENANT_ACME_ID, did.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.did import DIDUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = DIDService(mock_db)
        data = DIDUpdate(description="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_did(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateDid:
    async def test_success(self, mock_db):
        did = _make_did(is_active=True)
        mock_db.execute.return_value = make_scalar_result(did)
        service = DIDService(mock_db)
        await service.deactivate_did(TENANT_ACME_ID, did.id)
        assert did.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = DIDService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_did(TENANT_ACME_ID, uuid.uuid4())
