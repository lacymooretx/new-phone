"""Tests for new_phone.services.extension_service — extension CRUD + SIP creds."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.extension_service import (
    ExtensionService,
    _generate_sip_password,
    _generate_sip_username,
)
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result

# ── Helper function tests ──────────────────────────────────────────────────


class TestGenerateSipPassword:
    def test_default_length(self):
        pw = _generate_sip_password()
        assert len(pw) == 32

    def test_custom_length(self):
        pw = _generate_sip_password(length=16)
        assert len(pw) == 16

    def test_alphanumeric_only(self):
        pw = _generate_sip_password()
        assert pw.isalnum()

    def test_different_each_call(self):
        p1 = _generate_sip_password()
        p2 = _generate_sip_password()
        assert p1 != p2


class TestGenerateSipUsername:
    def test_format(self):
        tid = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        username = _generate_sip_username(tid, "100")
        assert username == "12345678-100"

    def test_includes_extension_number(self):
        tid = uuid.UUID("abcdef01-0000-0000-0000-000000000000")
        username = _generate_sip_username(tid, "2001")
        assert "2001" in username


# ── Service tests ──────────────────────────────────────────────────────────


def _make_extension(**overrides):
    """Quick mock extension for testing."""
    ext = MagicMock()
    ext.id = overrides.get("id", uuid.uuid4())
    ext.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    ext.extension_number = overrides.get("extension_number", "100")
    ext.sip_username = overrides.get("sip_username", "00000000-100")
    ext.is_active = overrides.get("is_active", True)
    ext.deactivated_at = overrides.get("deactivated_at")
    ext.sip_password_hash = overrides.get("sip_password_hash", "hash")
    ext.encrypted_sip_password = overrides.get("encrypted_sip_password", "enc")
    ext.agent_status = overrides.get("agent_status")
    return ext


class TestListExtensions:
    async def test_returns_list(self, mock_db):
        e1 = _make_extension(extension_number="100")
        e2 = _make_extension(extension_number="101")
        mock_db.execute.return_value = make_scalars_result([e1, e2])

        service = ExtensionService(mock_db)
        result = await service.list_extensions(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = ExtensionService(mock_db)
        result = await service.list_extensions(TENANT_ACME_ID)
        assert result == []


class TestGetExtension:
    async def test_found(self, mock_db):
        ext = _make_extension(extension_number="100")
        mock_db.execute.return_value = make_scalar_result(ext)
        service = ExtensionService(mock_db)
        result = await service.get_extension(TENANT_ACME_ID, ext.id)
        assert result.extension_number == "100"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ExtensionService(mock_db)
        result = await service.get_extension(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateExtension:
    async def test_success(self, mock_db):
        from new_phone.schemas.extension import ExtensionCreate

        # Duplicate check returns None
        mock_db.execute.return_value = make_scalar_result(None)

        service = ExtensionService(mock_db)
        data = ExtensionCreate(extension_number="200")
        await service.create_extension(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert added.extension_number == "200"
        assert added.sip_username.endswith("-200")
        assert added.sip_password_hash.startswith("$2b$")
        assert added.encrypted_sip_password is not None

    async def test_duplicate_number_raises(self, mock_db):
        from new_phone.schemas.extension import ExtensionCreate

        existing = _make_extension(extension_number="100")
        mock_db.execute.return_value = make_scalar_result(existing)

        service = ExtensionService(mock_db)
        data = ExtensionCreate(extension_number="100")
        with pytest.raises(ValueError, match="already exists"):
            await service.create_extension(TENANT_ACME_ID, data)


class TestUpdateExtension:
    async def test_success(self, mock_db):
        from new_phone.schemas.extension import ExtensionUpdate

        ext = _make_extension(extension_number="100")
        mock_db.execute.return_value = make_scalar_result(ext)

        service = ExtensionService(mock_db)
        data = ExtensionUpdate(notes="updated")
        await service.update_extension(TENANT_ACME_ID, ext.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.extension import ExtensionUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = ExtensionService(mock_db)
        data = ExtensionUpdate(notes="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_extension(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateExtension:
    async def test_success(self, mock_db):
        ext = _make_extension(is_active=True)
        mock_db.execute.return_value = make_scalar_result(ext)
        service = ExtensionService(mock_db)
        await service.deactivate_extension(TENANT_ACME_ID, ext.id)
        assert ext.is_active is False
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ExtensionService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_extension(TENANT_ACME_ID, uuid.uuid4())


class TestResetSipPassword:
    async def test_success(self, mock_db):
        ext = _make_extension()
        mock_db.execute.return_value = make_scalar_result(ext)
        service = ExtensionService(mock_db)
        new_pw = await service.reset_sip_password(TENANT_ACME_ID, ext.id)
        assert isinstance(new_pw, str)
        assert len(new_pw) == 32
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = ExtensionService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.reset_sip_password(TENANT_ACME_ID, uuid.uuid4())
