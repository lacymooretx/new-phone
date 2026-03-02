"""Tests for new_phone.services.voicemail_service — voicemail box CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.voicemail_service import VoicemailService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_vmbox(**overrides):
    box = MagicMock()
    box.id = overrides.get("id", uuid.uuid4())
    box.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    box.mailbox_number = overrides.get("mailbox_number", "100")
    box.is_active = overrides.get("is_active", True)
    box.pin_hash = overrides.get("pin_hash", "$2b$12$hash")
    box.encrypted_pin = overrides.get("encrypted_pin", "enc")
    box.deactivated_at = overrides.get("deactivated_at")
    return box


class TestListVoicemailBoxes:
    async def test_returns_list(self, mock_db):
        b1 = _make_vmbox(mailbox_number="100")
        b2 = _make_vmbox(mailbox_number="101")
        mock_db.execute.return_value = make_scalars_result([b1, b2])

        service = VoicemailService(mock_db)
        result = await service.list_voicemail_boxes(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = VoicemailService(mock_db)
        result = await service.list_voicemail_boxes(TENANT_ACME_ID)
        assert result == []


class TestGetVoicemailBox:
    async def test_found(self, mock_db):
        box = _make_vmbox(mailbox_number="100")
        mock_db.execute.return_value = make_scalar_result(box)
        service = VoicemailService(mock_db)
        result = await service.get_voicemail_box(TENANT_ACME_ID, box.id)
        assert result.mailbox_number == "100"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = VoicemailService(mock_db)
        result = await service.get_voicemail_box(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateVoicemailBox:
    async def test_success(self, mock_db):
        from new_phone.schemas.voicemail_box import VoicemailBoxCreate

        mock_db.execute.return_value = make_scalar_result(None)  # no duplicate

        service = VoicemailService(mock_db)
        data = VoicemailBoxCreate(mailbox_number="200", pin="1234")
        await service.create_voicemail_box(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert added.mailbox_number == "200"
        assert added.pin_hash.startswith("$2b$")
        assert added.encrypted_pin is not None

    async def test_duplicate_number_raises(self, mock_db):
        from new_phone.schemas.voicemail_box import VoicemailBoxCreate

        existing = _make_vmbox(mailbox_number="100")
        mock_db.execute.return_value = make_scalar_result(existing)

        service = VoicemailService(mock_db)
        data = VoicemailBoxCreate(mailbox_number="100", pin="1234")
        with pytest.raises(ValueError, match="already exists"):
            await service.create_voicemail_box(TENANT_ACME_ID, data)


class TestUpdateVoicemailBox:
    async def test_success(self, mock_db):
        from new_phone.schemas.voicemail_box import VoicemailBoxUpdate

        box = _make_vmbox()
        mock_db.execute.return_value = make_scalar_result(box)

        service = VoicemailService(mock_db)
        data = VoicemailBoxUpdate(max_messages=50)
        await service.update_voicemail_box(TENANT_ACME_ID, box.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.voicemail_box import VoicemailBoxUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = VoicemailService(mock_db)
        data = VoicemailBoxUpdate(max_messages=50)
        with pytest.raises(ValueError, match="not found"):
            await service.update_voicemail_box(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateVoicemailBox:
    async def test_success(self, mock_db):
        box = _make_vmbox(is_active=True)
        mock_db.execute.return_value = make_scalar_result(box)
        service = VoicemailService(mock_db)
        await service.deactivate_voicemail_box(TENANT_ACME_ID, box.id)
        assert box.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = VoicemailService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_voicemail_box(TENANT_ACME_ID, uuid.uuid4())


class TestResetPin:
    async def test_returns_4_digit_pin(self, mock_db):
        box = _make_vmbox()
        mock_db.execute.return_value = make_scalar_result(box)
        service = VoicemailService(mock_db)
        pin = await service.reset_pin(TENANT_ACME_ID, box.id)
        assert len(pin) == 4
        assert pin.isdigit()
        mock_db.commit.assert_awaited()
