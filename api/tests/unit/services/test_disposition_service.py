"""Tests for new_phone.services.disposition_service — disposition code list + code CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.disposition_service import DispositionService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_code_list(**overrides):
    cl = MagicMock()
    cl.id = overrides.get("id", uuid.uuid4())
    cl.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    cl.name = overrides.get("name", "Sales Dispositions")
    cl.is_active = overrides.get("is_active", True)
    return cl


def _make_code(**overrides):
    code = MagicMock()
    code.id = overrides.get("id", uuid.uuid4())
    code.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    code.list_id = overrides.get("list_id", uuid.uuid4())
    code.code = overrides.get("code", "SALE")
    code.label = overrides.get("label", "Completed Sale")
    code.is_active = overrides.get("is_active", True)
    return code


# ── Code Lists ──────────────────────────────────────────────────────────────


class TestListCodeLists:
    async def test_returns_list(self, mock_db):
        cl1 = _make_code_list(name="Sales")
        cl2 = _make_code_list(name="Support")
        mock_db.execute.return_value = make_scalars_result([cl1, cl2])

        service = DispositionService(mock_db)
        result = await service.list_code_lists(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = DispositionService(mock_db)
        result = await service.list_code_lists(TENANT_ACME_ID)
        assert result == []


class TestGetCodeList:
    async def test_found(self, mock_db):
        cl = _make_code_list(name="Sales")
        mock_db.execute.return_value = make_scalar_result(cl)
        service = DispositionService(mock_db)
        result = await service.get_code_list(TENANT_ACME_ID, cl.id)
        assert result.name == "Sales"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = DispositionService(mock_db)
        result = await service.get_code_list(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateCodeList:
    async def test_success(self, mock_db):
        from new_phone.schemas.disposition import DispositionCodeListCreate

        service = DispositionService(mock_db)
        data = DispositionCodeListCreate(name="New List")
        await service.create_code_list(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()


class TestUpdateCodeList:
    async def test_success(self, mock_db):
        from new_phone.schemas.disposition import DispositionCodeListUpdate

        cl = _make_code_list()
        mock_db.execute.return_value = make_scalar_result(cl)
        service = DispositionService(mock_db)
        data = DispositionCodeListUpdate(name="Updated List")
        await service.update_code_list(TENANT_ACME_ID, cl.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.disposition import DispositionCodeListUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = DispositionService(mock_db)
        data = DispositionCodeListUpdate(name="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_code_list(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateCodeList:
    async def test_success(self, mock_db):
        cl = _make_code_list(is_active=True)
        mock_db.execute.return_value = make_scalar_result(cl)
        service = DispositionService(mock_db)
        await service.deactivate_code_list(TENANT_ACME_ID, cl.id)
        assert cl.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = DispositionService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_code_list(TENANT_ACME_ID, uuid.uuid4())


# ── Codes ───────────────────────────────────────────────────────────────────


class TestCreateCode:
    async def test_success(self, mock_db):
        from new_phone.schemas.disposition import DispositionCodeCreate

        list_id = uuid.uuid4()
        cl = _make_code_list(id=list_id)
        mock_db.execute.side_effect = [
            make_scalar_result(cl),     # get_code_list
            make_scalar_result(None),   # uniqueness check
        ]

        service = DispositionService(mock_db)
        data = DispositionCodeCreate(code="NEW", label="New Code")
        await service.create_code(TENANT_ACME_ID, list_id, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    async def test_list_not_found_raises(self, mock_db):
        from new_phone.schemas.disposition import DispositionCodeCreate

        mock_db.execute.return_value = make_scalar_result(None)
        service = DispositionService(mock_db)
        data = DispositionCodeCreate(code="X", label="X")
        with pytest.raises(ValueError, match="not found"):
            await service.create_code(TENANT_ACME_ID, uuid.uuid4(), data)

    async def test_duplicate_code_raises(self, mock_db):
        from new_phone.schemas.disposition import DispositionCodeCreate

        list_id = uuid.uuid4()
        cl = _make_code_list(id=list_id)
        existing_code = _make_code(code="SALE", list_id=list_id)
        mock_db.execute.side_effect = [
            make_scalar_result(cl),              # get_code_list
            make_scalar_result(existing_code),   # uniqueness check fails
        ]

        service = DispositionService(mock_db)
        data = DispositionCodeCreate(code="SALE", label="Sale")
        with pytest.raises(ValueError, match="already exists"):
            await service.create_code(TENANT_ACME_ID, list_id, data)


class TestUpdateCode:
    async def test_success(self, mock_db):
        from new_phone.schemas.disposition import DispositionCodeUpdate

        code = _make_code()
        mock_db.execute.return_value = make_scalar_result(code)
        service = DispositionService(mock_db)
        data = DispositionCodeUpdate(label="Updated Label")
        await service.update_code(TENANT_ACME_ID, code.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.disposition import DispositionCodeUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = DispositionService(mock_db)
        data = DispositionCodeUpdate(label="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_code(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateCode:
    async def test_success(self, mock_db):
        code = _make_code(is_active=True)
        mock_db.execute.return_value = make_scalar_result(code)
        service = DispositionService(mock_db)
        await service.deactivate_code(TENANT_ACME_ID, code.id)
        assert code.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = DispositionService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_code(TENANT_ACME_ID, uuid.uuid4())
