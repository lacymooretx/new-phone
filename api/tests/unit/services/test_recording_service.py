"""Tests for new_phone.services.recording_service — recording CRUD, presigned URLs."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

from new_phone.schemas.recording import RecordingFilter
from new_phone.services.recording_service import RecordingService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_recording(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        cdr_id=uuid.uuid4(),
        call_id="call-abc-123",
        storage_path="recordings/tenant/call-abc-123.wav",
        storage_bucket="recordings",
        file_size_bytes=500000,
        duration_seconds=60,
        format="wav",
        sample_rate=8000,
        sha256_hash="def456",
        recording_policy="always",
        is_active=True,
        storage_tier="hot",
        archived_at=None,
        legal_hold=False,
        retrieval_requested_at=None,
        retrieval_expires_at=None,
        retention_expires_at=None,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListRecordings:
    async def test_returns_recordings(self, mock_db):
        r1 = _make_recording()
        r2 = _make_recording()
        mock_db.execute.return_value = make_scalars_result([r1, r2])

        service = RecordingService(mock_db)
        result = await service.list_recordings(TENANT_ACME_ID, RecordingFilter())
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = RecordingService(mock_db)
        result = await service.list_recordings(TENANT_ACME_ID, RecordingFilter())
        assert result == []

    async def test_filters_by_call_id(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([_make_recording()])
        service = RecordingService(mock_db)
        filters = RecordingFilter(call_id="call-abc-123")
        result = await service.list_recordings(TENANT_ACME_ID, filters)
        assert len(result) == 1

    async def test_filters_by_legal_hold(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = RecordingService(mock_db)
        filters = RecordingFilter(legal_hold=True)
        result = await service.list_recordings(TENANT_ACME_ID, filters)
        assert result == []


class TestGetRecording:
    async def test_found(self, mock_db):
        rec = _make_recording()
        mock_db.execute.return_value = make_scalar_result(rec)
        service = RecordingService(mock_db)
        result = await service.get_recording(TENANT_ACME_ID, rec.id)
        assert result is rec

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = RecordingService(mock_db)
        result = await service.get_recording(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestSoftDelete:
    async def test_success(self, mock_db):
        rec = _make_recording()
        mock_db.execute.return_value = make_scalar_result(rec)

        service = RecordingService(mock_db)
        await service.soft_delete(TENANT_ACME_ID, rec.id)
        assert rec.is_active is False
        mock_db.commit.assert_awaited_once()

    async def test_not_found_returns_none(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = RecordingService(mock_db)
        result = await service.soft_delete(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestGetPlaybackUrl:
    async def test_available(self, mock_db):
        rec = _make_recording(storage_tier="hot", storage_path="recordings/test.wav")
        mock_db.execute.return_value = make_scalar_result(rec)
        mock_storage = MagicMock()
        mock_storage.presigned_url.return_value = "https://s3.example.com/test.wav"

        service = RecordingService(mock_db, storage=mock_storage)
        result = await service.get_playback_url(TENANT_ACME_ID, rec.id)
        assert result["status"] == "available"
        assert result["url"] is not None

    async def test_cold_without_path_returns_cold(self, mock_db):
        rec = _make_recording(storage_tier="cold", storage_path=None)
        mock_db.execute.return_value = make_scalar_result(rec)
        mock_storage = MagicMock()

        service = RecordingService(mock_db, storage=mock_storage)
        result = await service.get_playback_url(TENANT_ACME_ID, rec.id)
        assert result["status"] == "cold"
        assert result["url"] is None

    async def test_missing_recording(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = RecordingService(mock_db, storage=MagicMock())
        result = await service.get_playback_url(TENANT_ACME_ID, uuid.uuid4())
        assert result["status"] == "missing"

    async def test_no_storage_service(self, mock_db):
        rec = _make_recording()
        mock_db.execute.return_value = make_scalar_result(rec)

        service = RecordingService(mock_db, storage=None)
        result = await service.get_playback_url(TENANT_ACME_ID, rec.id)
        assert result["status"] == "missing"

    async def test_missing_storage_path_returns_missing(self, mock_db):
        rec = _make_recording(storage_tier="hot", storage_path=None)
        mock_db.execute.return_value = make_scalar_result(rec)
        mock_storage = MagicMock()

        service = RecordingService(mock_db, storage=mock_storage)
        result = await service.get_playback_url(TENANT_ACME_ID, rec.id)
        assert result["status"] == "missing"
