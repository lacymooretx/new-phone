"""Tests for new_phone.services.dnc_service — DNC list/entry CRUD + check_number."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.dnc_service import DNCService
from tests.unit.conftest import (
    TENANT_ACME_ID,
    make_scalar_result,
    make_scalars_result,
)


def _make_dnc_list(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        name="Internal DNC",
        list_type="internal",
        is_active=True,
        description=None,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_entry(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        dnc_list_id=uuid.uuid4(),
        phone_number="+15551234567",
        source="manual",
        reason=None,
        added_by_user_id=None,
        created_at=None,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListDNCLists:
    async def test_returns_list(self, mock_db):
        l1 = _make_dnc_list(name="List A")
        l2 = _make_dnc_list(name="List B")
        mock_db.execute.return_value = make_scalars_result([l1, l2])

        service = DNCService(mock_db)
        result = await service.list_dnc_lists(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_returns_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = DNCService(mock_db)
        result = await service.list_dnc_lists(TENANT_ACME_ID)
        assert result == []


class TestGetDNCList:
    async def test_found(self, mock_db):
        dnc_list = _make_dnc_list()
        mock_db.execute.return_value = make_scalar_result(dnc_list)

        service = DNCService(mock_db)
        result = await service.get_dnc_list(TENANT_ACME_ID, dnc_list.id)
        assert result.name == "Internal DNC"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = DNCService(mock_db)
        result = await service.get_dnc_list(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateDNCList:
    async def test_success(self, mock_db):
        data = MagicMock()
        data.model_dump.return_value = {"name": "New DNC", "list_type": "internal"}
        data.name = "New DNC"

        service = DNCService(mock_db)
        await service.create_dnc_list(TENANT_ACME_ID, data)
        mock_db.add.assert_called()
        mock_db.commit.assert_awaited()


class TestUpdateDNCList:
    async def test_success(self, mock_db):
        dnc_list = _make_dnc_list(name="Old")
        mock_db.execute.return_value = make_scalar_result(dnc_list)

        data = MagicMock()
        data.model_dump.return_value = {"name": "Updated"}

        service = DNCService(mock_db)
        result = await service.update_dnc_list(TENANT_ACME_ID, dnc_list.id, data)
        assert result.name == "Updated"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = MagicMock()
        data.model_dump.return_value = {}

        service = DNCService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.update_dnc_list(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeleteDNCList:
    async def test_success(self, mock_db):
        dnc_list = _make_dnc_list(is_active=True)
        mock_db.execute.return_value = make_scalar_result(dnc_list)

        service = DNCService(mock_db)
        result = await service.delete_dnc_list(TENANT_ACME_ID, dnc_list.id)
        assert result.is_active is False
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = DNCService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.delete_dnc_list(TENANT_ACME_ID, uuid.uuid4())


class TestCheckNumber:
    async def test_blocked_number(self, mock_db):
        # Mock execute calls:
        # 1. set_tenant_context in check_number
        # 2. DNC list check - returns matched lists
        matched_result = MagicMock()
        matched_result.all.return_value = [("Internal DNC",)]
        # 3. Consent check - no consent
        consent_result = make_scalar_result(None)
        # 4. set_tenant_context in get_settings
        # 5. get_settings query
        settings_obj = MagicMock()
        settings_obj.enforce_calling_window = False
        settings_result = make_scalar_result(settings_obj)
        mock_db.execute.side_effect = [
            MagicMock(),  # set_tenant_context in check_number
            matched_result,
            consent_result,
            MagicMock(),  # set_tenant_context in get_settings
            settings_result,
        ]

        service = DNCService(mock_db)
        result = await service.check_number(TENANT_ACME_ID, "+15551234567")
        assert result.is_blocked is True
        assert "Internal DNC" in result.matched_lists

    async def test_not_blocked_number(self, mock_db):
        # No matches in DNC
        matched_result = MagicMock()
        matched_result.all.return_value = []
        # No consent
        consent_result = make_scalar_result(None)
        # Settings - no calling window enforcement
        settings_obj = MagicMock()
        settings_obj.enforce_calling_window = False
        settings_result = make_scalar_result(settings_obj)

        mock_db.execute.side_effect = [
            MagicMock(),  # set_tenant_context in check_number
            matched_result,
            consent_result,
            MagicMock(),  # set_tenant_context in get_settings
            settings_result,
        ]

        service = DNCService(mock_db)
        result = await service.check_number(TENANT_ACME_ID, "+15559999999")
        assert result.is_blocked is False
        assert result.matched_lists == []


class TestRemoveEntry:
    async def test_success(self, mock_db):
        entry = _make_entry()
        list_id = entry.dnc_list_id
        mock_db.execute.side_effect = [
            MagicMock(),  # set_tenant_context
            make_scalar_result(entry),  # select entry
            MagicMock(),  # delete
        ]

        service = DNCService(mock_db)
        await service.remove_entry(TENANT_ACME_ID, list_id, entry.id)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = DNCService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.remove_entry(TENANT_ACME_ID, uuid.uuid4(), uuid.uuid4())
