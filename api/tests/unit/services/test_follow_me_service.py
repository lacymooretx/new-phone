"""Tests for new_phone.services.follow_me_service — follow-me upsert."""

import uuid
from unittest.mock import MagicMock

from new_phone.services.follow_me_service import FollowMeService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result


def _make_follow_me(**overrides):
    fm = MagicMock()
    fm.id = overrides.get("id", uuid.uuid4())
    fm.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    fm.extension_id = overrides.get("extension_id", uuid.uuid4())
    fm.enabled = overrides.get("enabled", True)
    fm.strategy = overrides.get("strategy", "sequential")
    fm.ring_extension_first = overrides.get("ring_extension_first", True)
    fm.extension_ring_time = overrides.get("extension_ring_time", 25)
    fm.is_active = overrides.get("is_active", True)
    fm.destinations = overrides.get("destinations", [])
    return fm


class TestGetFollowMe:
    async def test_found(self, mock_db):
        fm = _make_follow_me(enabled=True)
        mock_db.execute.return_value = make_scalar_result(fm)
        service = FollowMeService(mock_db)
        result = await service.get_follow_me(TENANT_ACME_ID, fm.extension_id)
        assert result.enabled is True

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = FollowMeService(mock_db)
        result = await service.get_follow_me(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestUpsertFollowMe:
    async def test_creates_new(self, mock_db):
        from new_phone.schemas.follow_me import FollowMeDestinationData, FollowMeUpdate

        ext_id = uuid.uuid4()
        # No existing follow-me
        mock_db.execute.return_value = make_scalar_result(None)

        service = FollowMeService(mock_db)
        data = FollowMeUpdate(
            enabled=True,
            destinations=[FollowMeDestinationData(destination="5551234567", ring_time=20)],
        )
        await service.upsert_follow_me(TENANT_ACME_ID, ext_id, data)
        # FollowMe + 1 destination = 2 add calls
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_awaited()

    async def test_updates_existing(self, mock_db):
        from new_phone.schemas.follow_me import FollowMeDestinationData, FollowMeUpdate

        fm = _make_follow_me(enabled=False)
        mock_db.execute.side_effect = [
            make_scalar_result(fm),  # find existing
            MagicMock(),  # delete existing destinations
        ]

        service = FollowMeService(mock_db)
        data = FollowMeUpdate(
            enabled=True,
            destinations=[FollowMeDestinationData(destination="5559876543", ring_time=30)],
        )
        await service.upsert_follow_me(TENANT_ACME_ID, fm.extension_id, data)
        assert fm.enabled is True
        # 1 destination added
        assert mock_db.add.call_count == 1
        mock_db.commit.assert_awaited()
