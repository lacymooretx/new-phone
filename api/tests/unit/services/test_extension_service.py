"""Tests for new_phone.services.extension_service — extension CRUD + SIP credentials."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from new_phone.schemas.extension import ExtensionCreate, ExtensionUpdate
from new_phone.services.extension_service import ExtensionService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_ext(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        extension_number="1001",
        sip_username="00000000-1001",
        sip_password_hash="$2b$12$hash",
        encrypted_sip_password="encrypted",
        user_id=None,
        voicemail_box_id=None,
        internal_cid_name="Ext 1001",
        internal_cid_number="1001",
        external_cid_name=None,
        external_cid_number=None,
        emergency_cid_number=None,
        is_active=True,
        deactivated_at=None,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListExtensions:
    async def test_returns_active(self, mock_db):
        e1 = _make_ext(extension_number="1001")
        e2 = _make_ext(extension_number="1002")
        mock_db.execute.return_value = make_scalars_result([e1, e2])

        service = ExtensionService(mock_db)
        result = await service.list_extensions(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = ExtensionService(mock_db)
        result = await service.list_extensions(TENANT_ACME_ID)
        assert result == []

    async def test_filters_by_site(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([_make_ext()])
        service = ExtensionService(mock_db)
        result = await service.list_extensions(TENANT_ACME_ID, site_id=uuid.uuid4())
        assert len(result) == 1


class TestGetExtension:
    async def test_found(self, mock_db):
        ext = _make_ext()
        mock_db.execute.return_value = make_scalar_result(ext)
        service = ExtensionService(mock_db)
        result = await service.get_extension(TENANT_ACME_ID, ext.id)
        assert result is ext

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ExtensionService(mock_db)
        result = await service.get_extension(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateExtension:
    async def test_success_generates_sip_credentials(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = ExtensionCreate(extension_number="1005")

        service = ExtensionService(mock_db)
        await service.create_extension(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert added.sip_username is not None
        assert added.sip_password_hash is not None
        assert added.encrypted_sip_password is not None
        mock_db.commit.assert_awaited_once()

    async def test_duplicate_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(_make_ext())
        data = ExtensionCreate(extension_number="1001")

        service = ExtensionService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_extension(TENANT_ACME_ID, data)


class TestUpdateExtension:
    async def test_success(self, mock_db):
        ext = _make_ext()
        mock_db.execute.return_value = make_scalar_result(ext)
        data = ExtensionUpdate(internal_cid_name="John Doe")

        service = ExtensionService(mock_db)
        await service.update_extension(TENANT_ACME_ID, ext.id, data)
        assert ext.internal_cid_name == "John Doe"
        mock_db.commit.assert_awaited_once()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ExtensionService(mock_db)
        with pytest.raises(ValueError, match="Extension not found"):
            await service.update_extension(
                TENANT_ACME_ID, uuid.uuid4(), ExtensionUpdate(notes="x")
            )


class TestDeactivateExtension:
    async def test_success(self, mock_db):
        ext = _make_ext()
        mock_db.execute.return_value = make_scalar_result(ext)

        service = ExtensionService(mock_db)
        await service.deactivate_extension(TENANT_ACME_ID, ext.id)
        assert ext.is_active is False
        assert ext.deactivated_at is not None

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ExtensionService(mock_db)
        with pytest.raises(ValueError, match="Extension not found"):
            await service.deactivate_extension(TENANT_ACME_ID, uuid.uuid4())


class TestResetSipPassword:
    async def test_success_returns_new_password(self, mock_db):
        ext = _make_ext()
        mock_db.execute.return_value = make_scalar_result(ext)

        service = ExtensionService(mock_db)
        new_pw = await service.reset_sip_password(TENANT_ACME_ID, ext.id)
        assert isinstance(new_pw, str)
        assert len(new_pw) == 32
        mock_db.commit.assert_awaited_once()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ExtensionService(mock_db)
        with pytest.raises(ValueError, match="Extension not found"):
            await service.reset_sip_password(TENANT_ACME_ID, uuid.uuid4())
