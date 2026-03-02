"""Tests for new_phone.services.user_service — user CRUD."""

import uuid

import pytest

from new_phone.models.user import UserRole
from new_phone.schemas.user import UserCreate, UserUpdate
from new_phone.services.user_service import UserService
from tests.unit.conftest import (
    TENANT_ACME_ID,
    USER_ACME_ADMIN_ID,
    make_scalar_result,
    make_scalars_result,
    make_user,
)


class TestListUsers:
    async def test_returns_users(self, mock_db):
        u1 = make_user(email="alice@acme.com")
        u2 = make_user(email="bob@acme.com")
        mock_db.execute.return_value = make_scalars_result([u1, u2])

        service = UserService(mock_db)
        result = await service.list_users(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_returns_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = UserService(mock_db)
        result = await service.list_users(TENANT_ACME_ID)
        assert result == []


class TestGetUser:
    async def test_found(self, mock_db):
        user = make_user(id=USER_ACME_ADMIN_ID)
        mock_db.execute.return_value = make_scalar_result(user)
        service = UserService(mock_db)
        result = await service.get_user(TENANT_ACME_ID, USER_ACME_ADMIN_ID)
        assert result.id == USER_ACME_ADMIN_ID

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = UserService(mock_db)
        result = await service.get_user(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestGetUserByEmail:
    async def test_found(self, mock_db):
        user = make_user(email="alice@acme.com")
        mock_db.execute.return_value = make_scalar_result(user)
        service = UserService(mock_db)
        result = await service.get_user_by_email("alice@acme.com")
        assert result.email == "alice@acme.com"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = UserService(mock_db)
        result = await service.get_user_by_email("nobody@acme.com")
        assert result is None


class TestCreateUser:
    async def test_success(self, mock_db):
        # Email check returns None (not duplicate)
        mock_db.execute.return_value = make_scalar_result(None)

        service = UserService(mock_db)
        data = UserCreate(
            email="new@acme.com",
            password="secure-pass-123",
            first_name="New",
            last_name="User",
        )
        await service.create_user(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        added_user = mock_db.add.call_args[0][0]
        assert added_user.tenant_id == TENANT_ACME_ID
        assert added_user.email == "new@acme.com"
        # Password should be hashed, not plain
        assert added_user.password_hash != "secure-pass-123"
        assert added_user.password_hash.startswith("$2b$")

    async def test_duplicate_email_raises(self, mock_db):
        existing = make_user(email="taken@acme.com")
        mock_db.execute.return_value = make_scalar_result(existing)

        service = UserService(mock_db)
        data = UserCreate(
            email="taken@acme.com",
            password="whatever123",
            first_name="Dup",
            last_name="User",
        )
        with pytest.raises(ValueError, match="already exists"):
            await service.create_user(TENANT_ACME_ID, data)

    async def test_assigns_correct_role(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = UserService(mock_db)
        data = UserCreate(
            email="mgr@acme.com",
            password="securepass1",
            first_name="Mgr",
            last_name="User",
            role=UserRole.TENANT_MANAGER,
        )
        await service.create_user(TENANT_ACME_ID, data)
        added = mock_db.add.call_args[0][0]
        assert added.role == UserRole.TENANT_MANAGER


class TestUpdateUser:
    async def test_success(self, mock_db):
        user = make_user(id=USER_ACME_ADMIN_ID, first_name="Old")
        mock_db.execute.return_value = make_scalar_result(user)

        service = UserService(mock_db)
        data = UserUpdate(first_name="New")
        await service.update_user(TENANT_ACME_ID, USER_ACME_ADMIN_ID, data)
        assert user.first_name == "New"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = UserService(mock_db)
        data = UserUpdate(first_name="X")
        with pytest.raises(ValueError, match="not found"):
            await service.update_user(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateUser:
    async def test_success(self, mock_db):
        user = make_user(id=USER_ACME_ADMIN_ID, is_active=True)
        mock_db.execute.return_value = make_scalar_result(user)

        service = UserService(mock_db)
        await service.deactivate_user(TENANT_ACME_ID, USER_ACME_ADMIN_ID)
        assert user.is_active is False
        assert user.deactivated_at is not None

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = UserService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_user(TENANT_ACME_ID, uuid.uuid4())
