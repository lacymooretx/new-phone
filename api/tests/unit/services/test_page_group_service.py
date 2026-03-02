"""Tests for new_phone.services.page_group_service — page group CRUD + members."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.page_group_service import PageGroupService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_page_group(**overrides):
    pg = MagicMock()
    pg.id = overrides.get("id", uuid.uuid4())
    pg.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    pg.name = overrides.get("name", "Lobby Page")
    pg.page_number = overrides.get("page_number", "700")
    pg.is_active = overrides.get("is_active", True)
    pg.members = overrides.get("members", [])
    pg.deactivated_at = overrides.get("deactivated_at")
    return pg


class TestListPageGroups:
    async def test_returns_list(self, mock_db):
        g1 = _make_page_group(name="Lobby")
        g2 = _make_page_group(name="Warehouse")
        mock_db.execute.return_value = make_scalars_result([g1, g2])

        service = PageGroupService(mock_db)
        result = await service.list_groups(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = PageGroupService(mock_db)
        result = await service.list_groups(TENANT_ACME_ID)
        assert result == []


class TestGetPageGroup:
    async def test_found(self, mock_db):
        pg = _make_page_group(name="Lobby")
        mock_db.execute.return_value = make_scalar_result(pg)
        service = PageGroupService(mock_db)
        result = await service.get_group(TENANT_ACME_ID, pg.id)
        assert result.name == "Lobby"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = PageGroupService(mock_db)
        result = await service.get_group(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreatePageGroup:
    async def test_success(self, mock_db):
        from new_phone.schemas.page_group import PageGroupCreate, PageGroupMemberCreate

        ext_id = uuid.uuid4()
        mock_db.execute.side_effect = [
            make_scalar_result(None),  # name check
            make_scalar_result(None),  # page_number check
        ]
        service = PageGroupService(mock_db)
        data = PageGroupCreate(
            name="New Page Group",
            page_number="701",
            members=[PageGroupMemberCreate(extension_id=ext_id, position=1)],
        )
        await service.create_group(TENANT_ACME_ID, data)
        # group + 1 member = 2 add calls
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_awaited()

    async def test_duplicate_name_raises(self, mock_db):
        from new_phone.schemas.page_group import PageGroupCreate

        existing = _make_page_group(name="Lobby")
        mock_db.execute.return_value = make_scalar_result(existing)

        service = PageGroupService(mock_db)
        data = PageGroupCreate(name="Lobby", page_number="702")
        with pytest.raises(ValueError, match="already exists"):
            await service.create_group(TENANT_ACME_ID, data)

    async def test_duplicate_page_number_raises(self, mock_db):
        from new_phone.schemas.page_group import PageGroupCreate

        mock_db.execute.side_effect = [
            make_scalar_result(None),  # name check passes
            make_scalar_result(_make_page_group(page_number="700")),  # page_number duplicate
        ]
        service = PageGroupService(mock_db)
        data = PageGroupCreate(name="Unique Name", page_number="700")
        with pytest.raises(ValueError, match="already exists"):
            await service.create_group(TENANT_ACME_ID, data)


class TestUpdatePageGroup:
    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.page_group import PageGroupUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = PageGroupService(mock_db)
        data = PageGroupUpdate(name="Updated")
        with pytest.raises(ValueError, match="not found"):
            await service.update_group(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivatePageGroup:
    async def test_success(self, mock_db):
        pg = _make_page_group(is_active=True)
        mock_db.execute.return_value = make_scalar_result(pg)
        service = PageGroupService(mock_db)
        await service.deactivate(TENANT_ACME_ID, pg.id)
        assert pg.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = PageGroupService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate(TENANT_ACME_ID, uuid.uuid4())
