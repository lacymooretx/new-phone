"""Tests for new_phone.services.ivr_menu_service — IVR menu CRUD + options."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from new_phone.schemas.ivr_menu import IVRMenuCreate, IVRMenuOptionCreate, IVRMenuUpdate
from new_phone.services.ivr_menu_service import IVRMenuService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_menu(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        name="Main Menu",
        description="Main IVR",
        greet_long_prompt_id=None,
        greet_short_prompt_id=None,
        invalid_sound_prompt_id=None,
        exit_sound_prompt_id=None,
        timeout=10,
        max_failures=3,
        max_timeouts=3,
        inter_digit_timeout=2,
        digit_len=1,
        exit_destination_type=None,
        exit_destination_id=None,
        enabled=True,
        is_active=True,
        options=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListMenus:
    async def test_returns_menus(self, mock_db):
        m1 = _make_menu(name="Menu A")
        m2 = _make_menu(name="Menu B")
        mock_db.execute.return_value = make_scalars_result([m1, m2])

        service = IVRMenuService(mock_db)
        result = await service.list_menus(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = IVRMenuService(mock_db)
        result = await service.list_menus(TENANT_ACME_ID)
        assert result == []


class TestGetMenu:
    async def test_found(self, mock_db):
        menu = _make_menu()
        mock_db.execute.return_value = make_scalar_result(menu)
        service = IVRMenuService(mock_db)
        result = await service.get_menu(TENANT_ACME_ID, menu.id)
        assert result is menu

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = IVRMenuService(mock_db)
        result = await service.get_menu(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateMenu:
    async def test_success_with_options(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = IVRMenuCreate(
            name="New Menu",
            options=[
                IVRMenuOptionCreate(digits="1", action_type="extension"),
                IVRMenuOptionCreate(digits="2", action_type="queue"),
            ],
        )

        service = IVRMenuService(mock_db)
        await service.create_menu(TENANT_ACME_ID, data)
        # 1 menu + 2 options
        assert mock_db.add.call_count == 3
        mock_db.flush.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    async def test_duplicate_name_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(_make_menu())
        data = IVRMenuCreate(name="Main Menu")

        service = IVRMenuService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_menu(TENANT_ACME_ID, data)

    async def test_success_without_options(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = IVRMenuCreate(name="Empty Menu")

        service = IVRMenuService(mock_db)
        await service.create_menu(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()  # just the menu


class TestUpdateMenu:
    async def test_success(self, mock_db):
        menu = _make_menu()
        mock_db.execute.return_value = make_scalar_result(menu)
        data = IVRMenuUpdate(description="Updated IVR")

        service = IVRMenuService(mock_db)
        await service.update_menu(TENANT_ACME_ID, menu.id, data)
        assert menu.description == "Updated IVR"
        mock_db.commit.assert_awaited_once()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = IVRMenuService(mock_db)
        with pytest.raises(ValueError, match="IVR menu not found"):
            await service.update_menu(
                TENANT_ACME_ID, uuid.uuid4(), IVRMenuUpdate(name="X")
            )


class TestDeactivateMenu:
    async def test_success(self, mock_db):
        menu = _make_menu()
        mock_db.execute.return_value = make_scalar_result(menu)

        service = IVRMenuService(mock_db)
        await service.deactivate(TENANT_ACME_ID, menu.id)
        assert menu.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = IVRMenuService(mock_db)
        with pytest.raises(ValueError, match="IVR menu not found"):
            await service.deactivate(TENANT_ACME_ID, uuid.uuid4())
