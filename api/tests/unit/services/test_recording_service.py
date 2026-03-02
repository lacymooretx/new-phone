"""Tests for new_phone.services.recording_service — recording CRUD, presigned URLs."""

import uuid
from unittest.mock import MagicMock

from new_phone.services.recording_service import RecordingService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_recording(**overrides):
    rec = MagicMock()
    rec.id = overrides.get("id", uuid.uuid4())
    rec.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    rec.call_id = overrides.get("call_id", str(uuid.uuid4()))
    rec.storage_path = overrides.get("storage_path", "recordings/2024/01/test.wav")
    rec.storage_tier = overrides.get("storage_tier", "hot")
    rec.is_active = overrides.get("is_active", True)
    rec.legal_hold = overrides.get("legal_hold", False)
    return rec


def _make_filter(**overrides):
    from new_phone.schemas.recording import RecordingFilter

    defaults = dict(
        date_from=None,
        date_to=None,
        call_id=None,
        cdr_id=None,
        storage_tier=None,
        legal_hold=None,
        offset=0,
        limit=50,
    )
    defaults.update(overrides)
    return RecordingFilter(**defaults)


class TestListRecordings:
    async def test_returns_list(self, mock_db):
        r1 = _make_recording()
        r2 = _make_recording()
        mock_db.execute.return_value = make_scalars_result([r1, r2])

        service = RecordingService(mock_db)
        result = await service.list_recordings(TENANT_ACME_ID, _make_filter())
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = RecordingService(mock_db)
        result = await service.list_recordings(TENANT_ACME_ID, _make_filter())
        assert result == []

    async def test_with_storage_tier_filter(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = RecordingService(mock_db)
        await service.list_recordings(TENANT_ACME_ID, _make_filter(storage_tier="hot"))
        mock_db.execute.assert_awaited()


class TestGetRecording:
    async def test_found(self, mock_db):
        rec = _make_recording()
        mock_db.execute.return_value = make_scalar_result(rec)
        service = RecordingService(mock_db)
        result = await service.get_recording(TENANT_ACME_ID, rec.id)
        assert result.call_id == rec.call_id

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = RecordingService(mock_db)
        result = await service.get_recording(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestGetPlaybackUrl:
    async def test_available(self, mock_db):
        rec = _make_recording(storage_path="recordings/test.wav", storage_tier="hot")
        mock_db.execute.return_value = make_scalar_result(rec)

        mock_storage = MagicMock()
        mock_storage.presigned_url.return_value = "https://minio.local/recordings/test.wav?signed=1"

        service = RecordingService(mock_db, storage=mock_storage)
        result = await service.get_playback_url(TENANT_ACME_ID, rec.id)
        assert result["status"] == "available"
        assert "https://" in result["url"]

    async def test_missing_no_storage_service(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = RecordingService(mock_db, storage=None)
        result = await service.get_playback_url(TENANT_ACME_ID, uuid.uuid4())
        assert result["status"] == "missing"
        assert result["url"] is None

    async def test_cold_no_path(self, mock_db):
        rec = _make_recording(storage_tier="cold", storage_path=None)
        mock_db.execute.return_value = make_scalar_result(rec)
        service = RecordingService(mock_db, storage=MagicMock())
        result = await service.get_playback_url(TENANT_ACME_ID, rec.id)
        assert result["status"] == "cold"


class TestSoftDelete:
    async def test_success(self, mock_db):
        rec = _make_recording(is_active=True)
        mock_db.execute.return_value = make_scalar_result(rec)
        service = RecordingService(mock_db)
        await service.soft_delete(TENANT_ACME_ID, rec.id)
        assert rec.is_active is False

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = RecordingService(mock_db)
        result = await service.soft_delete(TENANT_ACME_ID, uuid.uuid4())
        assert result is None
