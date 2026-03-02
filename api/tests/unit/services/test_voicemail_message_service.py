"""Tests for new_phone.services.voicemail_message_service — voicemail message CRUD."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

from new_phone.schemas.voicemail_message import VoicemailMessageFilter, VoicemailMessageUpdate
from new_phone.services.voicemail_message_service import VoicemailMessageService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_vm_msg(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        voicemail_box_id=uuid.uuid4(),
        caller_number="+15551234567",
        caller_name="John Doe",
        duration_seconds=30,
        storage_path="voicemail/tenant/msg.wav",
        storage_bucket="voicemail",
        file_size_bytes=120000,
        format="wav",
        sha256_hash="abc123",
        is_read=False,
        is_urgent=False,
        folder="new",
        call_id="call-123",
        email_sent=False,
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListMessages:
    async def test_returns_messages(self, mock_db):
        msg1 = _make_vm_msg()
        msg2 = _make_vm_msg()
        mock_db.execute.return_value = make_scalars_result([msg1, msg2])

        service = VoicemailMessageService(mock_db)
        box_id = msg1.voicemail_box_id
        filters = VoicemailMessageFilter()
        result = await service.list_messages(TENANT_ACME_ID, box_id, filters)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = VoicemailMessageService(mock_db)
        result = await service.list_messages(
            TENANT_ACME_ID, uuid.uuid4(), VoicemailMessageFilter()
        )
        assert result == []

    async def test_filters_by_folder(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([_make_vm_msg(folder="new")])
        service = VoicemailMessageService(mock_db)
        filters = VoicemailMessageFilter(folder="new")
        result = await service.list_messages(TENANT_ACME_ID, uuid.uuid4(), filters)
        assert len(result) == 1


class TestGetMessage:
    async def test_found(self, mock_db):
        msg = _make_vm_msg()
        mock_db.execute.return_value = make_scalar_result(msg)
        service = VoicemailMessageService(mock_db)
        result = await service.get_message(TENANT_ACME_ID, msg.voicemail_box_id, msg.id)
        assert result is msg

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = VoicemailMessageService(mock_db)
        result = await service.get_message(TENANT_ACME_ID, uuid.uuid4(), uuid.uuid4())
        assert result is None


class TestMarkRead:
    async def test_mark_read(self, mock_db):
        msg = _make_vm_msg(is_read=False)
        mock_db.execute.return_value = make_scalar_result(msg)
        data = VoicemailMessageUpdate(is_read=True)

        service = VoicemailMessageService(mock_db)
        await service.update_message(
            TENANT_ACME_ID, msg.voicemail_box_id, msg.id, data
        )
        assert msg.is_read is True
        mock_db.commit.assert_awaited_once()

    async def test_not_found_returns_none(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = VoicemailMessageService(mock_db)
        result = await service.update_message(
            TENANT_ACME_ID, uuid.uuid4(), uuid.uuid4(),
            VoicemailMessageUpdate(is_read=True)
        )
        assert result is None


class TestSoftDelete:
    async def test_success(self, mock_db):
        msg = _make_vm_msg()
        mock_db.execute.return_value = make_scalar_result(msg)

        service = VoicemailMessageService(mock_db)
        await service.soft_delete(TENANT_ACME_ID, msg.voicemail_box_id, msg.id)
        assert msg.is_active is False
        assert msg.folder == "deleted"
        mock_db.commit.assert_awaited_once()

    async def test_not_found_returns_none(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = VoicemailMessageService(mock_db)
        result = await service.soft_delete(TENANT_ACME_ID, uuid.uuid4(), uuid.uuid4())
        assert result is None


class TestGetPlaybackUrl:
    async def test_returns_url(self, mock_db):
        msg = _make_vm_msg(storage_path="voicemail/test.wav")
        mock_db.execute.return_value = make_scalar_result(msg)
        mock_storage = MagicMock()
        mock_storage.presigned_url.return_value = "https://s3.example.com/test.wav?sig=abc"

        service = VoicemailMessageService(mock_db, storage=mock_storage)
        result = await service.get_playback_url(
            TENANT_ACME_ID, msg.voicemail_box_id, msg.id
        )
        assert result is not None
        assert "https://" in result

    async def test_returns_none_when_no_storage(self, mock_db):
        msg = _make_vm_msg(storage_path=None)
        mock_db.execute.return_value = make_scalar_result(msg)

        service = VoicemailMessageService(mock_db, storage=None)
        result = await service.get_playback_url(
            TENANT_ACME_ID, msg.voicemail_box_id, msg.id
        )
        assert result is None
