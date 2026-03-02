"""Tests for new_phone.deps.auth — FastAPI dependency functions."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import (
    get_current_user,
    require_permission,
    require_role,
    require_tenant_access,
)
from new_phone.models.user import UserRole
from tests.unit.conftest import (
    TENANT_ACME_ID,
    TENANT_GLOBEX_ID,
    USER_ACME_ADMIN_ID,
    make_scalar_result,
    make_user,
)


def _make_credentials(token="fake-jwt-token"):
    creds = MagicMock()
    creds.credentials = token
    return creds


class TestGetCurrentUser:
    async def test_valid_token_returns_user(self, mock_db):
        user = make_user(id=USER_ACME_ADMIN_ID, role=UserRole.TENANT_ADMIN)
        mock_db.execute.return_value = make_scalar_result(user)

        with patch("new_phone.deps.auth.decode_token") as mock_decode:
            mock_decode.return_value = {
                "sub": str(USER_ACME_ADMIN_ID),
                "type": "access",
                "tenant_id": str(TENANT_ACME_ID),
                "role": "tenant_admin",
            }
            result = await get_current_user(_make_credentials(), mock_db)
            assert result.id == USER_ACME_ADMIN_ID

    async def test_invalid_token_raises_401(self, mock_db):
        from jose import JWTError

        with patch("new_phone.deps.auth.decode_token", side_effect=JWTError("bad")):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(_make_credentials(), mock_db)
            assert exc_info.value.status_code == 401

    async def test_non_access_token_raises_401(self, mock_db):
        with patch("new_phone.deps.auth.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": str(USER_ACME_ADMIN_ID), "type": "refresh"}
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(_make_credentials(), mock_db)
            assert exc_info.value.status_code == 401
            assert "token type" in exc_info.value.detail

    async def test_missing_sub_raises_401(self, mock_db):
        with patch("new_phone.deps.auth.decode_token") as mock_decode:
            mock_decode.return_value = {"type": "access"}
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(_make_credentials(), mock_db)
            assert exc_info.value.status_code == 401

    async def test_user_not_found_raises_401(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        with patch("new_phone.deps.auth.decode_token") as mock_decode:
            mock_decode.return_value = {
                "sub": str(uuid.uuid4()),
                "type": "access",
            }
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(_make_credentials(), mock_db)
            assert exc_info.value.status_code == 401

    async def test_inactive_user_raises_401(self, mock_db):
        user = make_user(id=USER_ACME_ADMIN_ID, is_active=False)
        mock_db.execute.return_value = make_scalar_result(user)
        with patch("new_phone.deps.auth.decode_token") as mock_decode:
            mock_decode.return_value = {
                "sub": str(USER_ACME_ADMIN_ID),
                "type": "access",
            }
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(_make_credentials(), mock_db)
            assert exc_info.value.status_code == 401


class TestRequireRole:
    async def test_matching_role_passes(self):
        user = make_user(role=UserRole.TENANT_ADMIN)
        checker = require_role(UserRole.TENANT_ADMIN, UserRole.MSP_SUPER_ADMIN)
        result = await checker(user)
        assert result.role == UserRole.TENANT_ADMIN

    async def test_non_matching_role_raises_403(self):
        user = make_user(role=UserRole.TENANT_USER)
        checker = require_role(UserRole.TENANT_ADMIN)
        with pytest.raises(HTTPException) as exc_info:
            await checker(user)
        assert exc_info.value.status_code == 403


class TestRequirePermission:
    async def test_user_with_permission_passes(self):
        user = make_user(role=UserRole.MSP_SUPER_ADMIN)
        checker = require_permission(Permission.MANAGE_PLATFORM)
        result = await checker(user)
        assert result.role == UserRole.MSP_SUPER_ADMIN

    async def test_user_without_permission_raises_403(self):
        user = make_user(role=UserRole.TENANT_USER)
        checker = require_permission(Permission.MANAGE_PLATFORM)
        with pytest.raises(HTTPException) as exc_info:
            await checker(user)
        assert exc_info.value.status_code == 403
        assert "manage_platform" in str(exc_info.value.detail).lower()


class TestRequireTenantAccess:
    async def test_msp_role_can_access_any_tenant(self):
        user = make_user(role=UserRole.MSP_SUPER_ADMIN, tenant_id=TENANT_ACME_ID)
        checker = require_tenant_access()
        result = await checker(user, tenant_id=str(TENANT_GLOBEX_ID))
        assert result.role == UserRole.MSP_SUPER_ADMIN

    async def test_tenant_user_can_access_own_tenant(self):
        user = make_user(role=UserRole.TENANT_ADMIN, tenant_id=TENANT_ACME_ID)
        checker = require_tenant_access()
        result = await checker(user, tenant_id=str(TENANT_ACME_ID))
        assert result is user

    async def test_tenant_user_cannot_access_other_tenant(self):
        user = make_user(role=UserRole.TENANT_ADMIN, tenant_id=TENANT_ACME_ID)
        checker = require_tenant_access()
        with pytest.raises(HTTPException) as exc_info:
            await checker(user, tenant_id=str(TENANT_GLOBEX_ID))
        assert exc_info.value.status_code == 403
