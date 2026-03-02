"""Tests for new_phone.auth.rbac — role-permission map, helper functions."""

from new_phone.auth.rbac import (
    ROLE_PERMISSIONS,
    Permission,
    has_permission,
    is_msp_role,
)
from new_phone.models.user import UserRole


class TestRolePermissionsMap:
    def test_all_five_roles_present(self):
        expected = {
            UserRole.MSP_SUPER_ADMIN,
            UserRole.MSP_TECH,
            UserRole.TENANT_ADMIN,
            UserRole.TENANT_MANAGER,
            UserRole.TENANT_USER,
        }
        assert set(ROLE_PERMISSIONS.keys()) == expected

    def test_msp_super_admin_has_manage_platform(self):
        assert Permission.MANAGE_PLATFORM in ROLE_PERMISSIONS[UserRole.MSP_SUPER_ADMIN]

    def test_msp_super_admin_has_all_permissions(self):
        all_perms = set(Permission)
        admin_perms = ROLE_PERMISSIONS[UserRole.MSP_SUPER_ADMIN]
        # MSP Super Admin should have every defined permission
        assert all_perms == admin_perms

    def test_msp_tech_no_manage_platform(self):
        assert Permission.MANAGE_PLATFORM not in ROLE_PERMISSIONS[UserRole.MSP_TECH]

    def test_msp_tech_has_view_all_tenants(self):
        assert Permission.VIEW_ALL_TENANTS in ROLE_PERMISSIONS[UserRole.MSP_TECH]

    def test_tenant_admin_no_view_all_tenants(self):
        assert Permission.VIEW_ALL_TENANTS not in ROLE_PERMISSIONS[UserRole.TENANT_ADMIN]

    def test_tenant_admin_has_manage_tenant(self):
        assert Permission.MANAGE_TENANT in ROLE_PERMISSIONS[UserRole.TENANT_ADMIN]

    def test_tenant_manager_no_manage_tenant(self):
        assert Permission.MANAGE_TENANT not in ROLE_PERMISSIONS[UserRole.TENANT_MANAGER]

    def test_tenant_manager_has_view_tenant(self):
        assert Permission.VIEW_TENANT in ROLE_PERMISSIONS[UserRole.TENANT_MANAGER]

    def test_tenant_user_has_view_own_profile(self):
        assert Permission.VIEW_OWN_PROFILE in ROLE_PERMISSIONS[UserRole.TENANT_USER]

    def test_tenant_user_no_manage_users(self):
        assert Permission.MANAGE_USERS not in ROLE_PERMISSIONS[UserRole.TENANT_USER]

    def test_tenant_user_has_place_calls(self):
        assert Permission.PLACE_CALLS in ROLE_PERMISSIONS[UserRole.TENANT_USER]

    def test_tenant_user_minimal_permissions(self):
        user_perms = ROLE_PERMISSIONS[UserRole.TENANT_USER]
        admin_perms = ROLE_PERMISSIONS[UserRole.TENANT_ADMIN]
        assert len(user_perms) < len(admin_perms)


class TestHasPermission:
    def test_returns_true_for_valid(self):
        assert has_permission(UserRole.MSP_SUPER_ADMIN, Permission.MANAGE_PLATFORM) is True

    def test_returns_false_for_missing(self):
        assert has_permission(UserRole.TENANT_USER, Permission.MANAGE_PLATFORM) is False

    def test_returns_false_for_unknown_role(self):
        assert has_permission("nonexistent_role", Permission.MANAGE_PLATFORM) is False


class TestIsMspRole:
    def test_msp_super_admin(self):
        assert is_msp_role(UserRole.MSP_SUPER_ADMIN) is True

    def test_msp_tech(self):
        assert is_msp_role(UserRole.MSP_TECH) is True

    def test_tenant_admin(self):
        assert is_msp_role(UserRole.TENANT_ADMIN) is False

    def test_tenant_manager(self):
        assert is_msp_role(UserRole.TENANT_MANAGER) is False

    def test_tenant_user(self):
        assert is_msp_role(UserRole.TENANT_USER) is False
