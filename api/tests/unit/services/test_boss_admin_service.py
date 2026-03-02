"""Tests for new_phone.services.boss_admin_service — boss/admin relationship CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.boss_admin_service import BossAdminService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_relationship(**overrides):
    rel = MagicMock()
    rel.id = overrides.get("id", uuid.uuid4())
    rel.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    rel.executive_extension_id = overrides.get("executive_extension_id", uuid.uuid4())
    rel.assistant_extension_id = overrides.get("assistant_extension_id", uuid.uuid4())
    rel.filter_mode = overrides.get("filter_mode", "all_to_assistant")
    rel.is_active = overrides.get("is_active", True)
    return rel


def _make_extension(**overrides):
    ext = MagicMock()
    ext.id = overrides.get("id", uuid.uuid4())
    ext.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    ext.extension_number = overrides.get("extension_number", "100")
    return ext


class TestListRelationships:
    async def test_returns_list(self, mock_db):
        r1 = _make_relationship()
        r2 = _make_relationship()
        mock_db.execute.return_value = make_scalars_result([r1, r2])

        service = BossAdminService(mock_db)
        result = await service.list_relationships(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = BossAdminService(mock_db)
        result = await service.list_relationships(TENANT_ACME_ID)
        assert result == []


class TestGetRelationship:
    async def test_found(self, mock_db):
        rel = _make_relationship()
        mock_db.execute.return_value = make_scalar_result(rel)
        service = BossAdminService(mock_db)
        result = await service.get_relationship(TENANT_ACME_ID, rel.id)
        assert result is not None

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = BossAdminService(mock_db)
        result = await service.get_relationship(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateRelationship:
    async def test_success(self, mock_db):
        from new_phone.schemas.boss_admin import BossAdminCreate

        exec_id = uuid.uuid4()
        asst_id = uuid.uuid4()
        exec_ext = _make_extension(id=exec_id)
        asst_ext = _make_extension(id=asst_id)

        mock_db.execute.side_effect = [
            make_scalar_result(exec_ext),   # validate executive extension
            make_scalar_result(asst_ext),   # validate assistant extension
            make_scalar_result(None),       # no duplicate
        ]

        service = BossAdminService(mock_db)
        data = BossAdminCreate(
            executive_extension_id=exec_id,
            assistant_extension_id=asst_id,
        )
        await service.create_relationship(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_same_extension_raises(self, mock_db):
        from new_phone.schemas.boss_admin import BossAdminCreate

        ext_id = uuid.uuid4()
        service = BossAdminService(mock_db)
        data = BossAdminCreate(
            executive_extension_id=ext_id,
            assistant_extension_id=ext_id,
        )
        with pytest.raises(ValueError, match="different extensions"):
            await service.create_relationship(TENANT_ACME_ID, data)

    async def test_executive_extension_not_found_raises(self, mock_db):
        from new_phone.schemas.boss_admin import BossAdminCreate

        mock_db.execute.return_value = make_scalar_result(None)

        service = BossAdminService(mock_db)
        data = BossAdminCreate(
            executive_extension_id=uuid.uuid4(),
            assistant_extension_id=uuid.uuid4(),
        )
        with pytest.raises(ValueError, match="Executive extension not found"):
            await service.create_relationship(TENANT_ACME_ID, data)

    async def test_duplicate_relationship_raises(self, mock_db):
        from new_phone.schemas.boss_admin import BossAdminCreate

        exec_id = uuid.uuid4()
        asst_id = uuid.uuid4()
        existing = _make_relationship(
            executive_extension_id=exec_id,
            assistant_extension_id=asst_id,
        )

        mock_db.execute.side_effect = [
            make_scalar_result(_make_extension(id=exec_id)),  # validate exec
            make_scalar_result(_make_extension(id=asst_id)),  # validate asst
            make_scalar_result(existing),  # duplicate found
        ]

        service = BossAdminService(mock_db)
        data = BossAdminCreate(
            executive_extension_id=exec_id,
            assistant_extension_id=asst_id,
        )
        with pytest.raises(ValueError, match="already exists"):
            await service.create_relationship(TENANT_ACME_ID, data)


class TestUpdateRelationship:
    async def test_success(self, mock_db):
        from new_phone.schemas.boss_admin import BossAdminUpdate

        rel = _make_relationship()
        mock_db.execute.return_value = make_scalar_result(rel)
        service = BossAdminService(mock_db)
        data = BossAdminUpdate(filter_mode="vip_only")
        await service.update_relationship(TENANT_ACME_ID, rel.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.boss_admin import BossAdminUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = BossAdminService(mock_db)
        data = BossAdminUpdate(filter_mode="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_relationship(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeleteRelationship:
    async def test_success(self, mock_db):
        rel = _make_relationship()
        mock_db.execute.return_value = make_scalar_result(rel)
        service = BossAdminService(mock_db)
        await service.delete_relationship(TENANT_ACME_ID, rel.id)
        mock_db.delete.assert_awaited_once_with(rel)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = BossAdminService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.delete_relationship(TENANT_ACME_ID, uuid.uuid4())
