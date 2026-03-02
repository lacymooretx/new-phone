"""Tests for new_phone.services.auth_service — login, MFA, refresh, lockout."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from new_phone.services.auth_service import AuthService
from tests.unit.conftest import TENANT_ACME_ID, USER_ACME_ADMIN_ID, make_scalar_result, make_user


class TestAuthenticate:
    async def test_success_no_mfa(self, mock_db):
        user = make_user(
            id=USER_ACME_ADMIN_ID,
            email="admin@acme.com",
            mfa_enabled=False,
        )
        # Hash a known password
        from new_phone.auth.passwords import hash_password

        user.password_hash = hash_password("correct-password")
        # execute calls: 1) user lookup, 2) SSO check
        mock_db.execute.side_effect = [
            make_scalar_result(user),
            make_scalar_result(None),  # no SSO provider
        ]
        service = AuthService(mock_db)
        result = await service.authenticate("admin@acme.com", "correct-password")
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"

    async def test_success_with_mfa_returns_challenge(self, mock_db):
        user = make_user(
            id=USER_ACME_ADMIN_ID,
            email="admin@acme.com",
            mfa_enabled=True,
            mfa_secret="JBSWY3DPEHPK3PXP",
        )
        from new_phone.auth.passwords import hash_password

        user.password_hash = hash_password("correct-password")
        mock_db.execute.side_effect = [
            make_scalar_result(user),
            make_scalar_result(None),
        ]
        service = AuthService(mock_db)
        result = await service.authenticate("admin@acme.com", "correct-password")
        assert result["mfa_required"] is True
        assert "mfa_token" in result

    async def test_wrong_password_raises(self, mock_db):
        user = make_user(email="admin@acme.com")
        from new_phone.auth.passwords import hash_password

        user.password_hash = hash_password("correct-password")
        mock_db.execute.side_effect = [
            make_scalar_result(user),
            make_scalar_result(None),
        ]
        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="Invalid email or password"):
            await service.authenticate("admin@acme.com", "wrong-password")

    async def test_user_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="Invalid email or password"):
            await service.authenticate("nobody@acme.com", "any-password")

    async def test_inactive_user_raises(self, mock_db):
        user = make_user(email="admin@acme.com", is_active=False)
        mock_db.execute.return_value = make_scalar_result(user)
        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="deactivated"):
            await service.authenticate("admin@acme.com", "any-password")

    async def test_sso_enforced_raises(self, mock_db):
        user = make_user(email="admin@acme.com")
        sso_provider = MagicMock()
        mock_db.execute.side_effect = [
            make_scalar_result(user),
            make_scalar_result(sso_provider),  # SSO is enforced
        ]
        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="SSO"):
            await service.authenticate("admin@acme.com", "any-password")

    async def test_lockout_after_max_attempts(self, mock_db):
        user = make_user(email="admin@acme.com", failed_login_attempts=4)
        from new_phone.auth.passwords import hash_password

        user.password_hash = hash_password("correct-password")
        mock_db.execute.side_effect = [
            make_scalar_result(user),
            make_scalar_result(None),
        ]
        service = AuthService(mock_db)
        # 5th wrong attempt → lockout
        with pytest.raises(ValueError, match="Invalid email or password"):
            await service.authenticate("admin@acme.com", "wrong")
        assert user.failed_login_attempts == 5
        assert user.locked_until is not None

    async def test_locked_account_raises(self, mock_db):
        user = make_user(
            email="admin@acme.com",
            locked_until=datetime.now(UTC) + timedelta(minutes=10),
        )
        from new_phone.auth.passwords import hash_password

        user.password_hash = hash_password("correct-password")
        mock_db.execute.side_effect = [
            make_scalar_result(user),
            make_scalar_result(None),
        ]
        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="locked"):
            await service.authenticate("admin@acme.com", "correct-password")

    async def test_resets_failed_attempts_on_success(self, mock_db):
        user = make_user(email="admin@acme.com", failed_login_attempts=3, mfa_enabled=False)
        from new_phone.auth.passwords import hash_password

        user.password_hash = hash_password("correct-password")
        mock_db.execute.side_effect = [
            make_scalar_result(user),
            make_scalar_result(None),
        ]
        service = AuthService(mock_db)
        await service.authenticate("admin@acme.com", "correct-password")
        assert user.failed_login_attempts == 0
        assert user.locked_until is None


class TestCompleteMfaChallenge:
    async def test_success(self, mock_db):
        from new_phone.auth.encryption import encrypt_value
        from new_phone.auth.jwt import create_mfa_token
        from new_phone.auth.mfa import generate_totp_secret

        secret = generate_totp_secret()
        user = make_user(id=USER_ACME_ADMIN_ID, mfa_enabled=True, mfa_secret=encrypt_value(secret))
        mfa_token = create_mfa_token(USER_ACME_ADMIN_ID)
        mock_db.execute.return_value = make_scalar_result(user)

        import pyotp

        code = pyotp.TOTP(secret).now()
        service = AuthService(mock_db)
        result = await service.complete_mfa_challenge(mfa_token, code)
        assert "access_token" in result

    async def test_invalid_token_type_raises(self, mock_db):
        from new_phone.auth.jwt import create_access_token

        # Use an access token instead of MFA token
        token = create_access_token(USER_ACME_ADMIN_ID, TENANT_ACME_ID, "tenant_admin")
        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="Invalid MFA token"):
            await service.complete_mfa_challenge(token, "123456")

    async def test_wrong_code_raises(self, mock_db):
        from new_phone.auth.encryption import encrypt_value
        from new_phone.auth.jwt import create_mfa_token
        from new_phone.auth.mfa import generate_totp_secret

        secret = generate_totp_secret()
        user = make_user(id=USER_ACME_ADMIN_ID, mfa_secret=encrypt_value(secret))
        mfa_token = create_mfa_token(USER_ACME_ADMIN_ID)
        mock_db.execute.return_value = make_scalar_result(user)

        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="Invalid MFA code"):
            await service.complete_mfa_challenge(mfa_token, "000000")


class TestRefreshTokens:
    async def test_success(self, mock_db):
        from new_phone.auth.jwt import create_refresh_token
        from new_phone.auth.passwords import hash_token

        refresh, _ = create_refresh_token(USER_ACME_ADMIN_ID)
        user = make_user(
            id=USER_ACME_ADMIN_ID,
            refresh_token_hash=hash_token(refresh),
        )
        mock_db.execute.return_value = make_scalar_result(user)

        service = AuthService(mock_db)
        result = await service.refresh_tokens(refresh)
        assert "access_token" in result
        assert "refresh_token" in result

    async def test_invalid_token_type_raises(self, mock_db):
        from new_phone.auth.jwt import create_access_token

        access = create_access_token(USER_ACME_ADMIN_ID, TENANT_ACME_ID, "tenant_admin")
        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="Invalid refresh token"):
            await service.refresh_tokens(access)

    async def test_user_not_found_raises(self, mock_db):
        from new_phone.auth.jwt import create_refresh_token

        refresh, _ = create_refresh_token(USER_ACME_ADMIN_ID)
        mock_db.execute.return_value = make_scalar_result(None)

        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="not found or inactive"):
            await service.refresh_tokens(refresh)

    async def test_hash_mismatch_raises(self, mock_db):
        from new_phone.auth.jwt import create_refresh_token

        refresh, _ = create_refresh_token(USER_ACME_ADMIN_ID)
        user = make_user(
            id=USER_ACME_ADMIN_ID,
            refresh_token_hash="wrong-hash-value",
        )
        mock_db.execute.return_value = make_scalar_result(user)

        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="Invalid refresh token"):
            await service.refresh_tokens(refresh)


class TestSetupMfa:
    async def test_returns_secret_and_qr(self, mock_db):
        from new_phone.auth.encryption import decrypt_value

        user = make_user(email="user@acme.com")
        service = AuthService(mock_db)
        result = await service.setup_mfa(user)
        assert "secret" in result
        assert "qr_code" in result
        assert "provisioning_uri" in result
        # mfa_secret is now stored encrypted; decrypt to compare
        assert decrypt_value(user.mfa_secret) == result["secret"]


class TestVerifyMfaSetup:
    async def test_success(self, mock_db):
        from new_phone.auth.encryption import encrypt_value
        from new_phone.auth.mfa import generate_totp_secret

        secret = generate_totp_secret()
        user = make_user(mfa_secret=encrypt_value(secret), mfa_enabled=False)

        import pyotp

        code = pyotp.TOTP(secret).now()
        service = AuthService(mock_db)
        result = await service.verify_mfa_setup(user, code)
        assert result is True
        assert user.mfa_enabled is True

    async def test_no_secret_raises(self, mock_db):
        user = make_user(mfa_secret=None)
        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="not set up"):
            await service.verify_mfa_setup(user, "123456")

    async def test_wrong_code_raises(self, mock_db):
        from new_phone.auth.encryption import encrypt_value
        from new_phone.auth.mfa import generate_totp_secret

        secret = generate_totp_secret()
        user = make_user(mfa_secret=encrypt_value(secret))
        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="Invalid code"):
            await service.verify_mfa_setup(user, "000000")


class TestChangePassword:
    async def test_success(self, mock_db):
        from new_phone.auth.passwords import hash_password

        user = make_user(
            id=USER_ACME_ADMIN_ID,
            email="admin@acme.com",
            password_hash=hash_password("old-password"),
        )
        mock_db.execute.return_value = make_scalar_result(user)
        service = AuthService(mock_db)
        result = await service.change_password(
            USER_ACME_ADMIN_ID, "old-password", "new-password-123"
        )
        assert result is True
        # Verify the hash was updated (no longer matches old password)
        from new_phone.auth.passwords import verify_password

        assert verify_password("new-password-123", user.password_hash)
        assert not verify_password("old-password", user.password_hash)
        mock_db.commit.assert_awaited()

    async def test_wrong_current_password_raises(self, mock_db):
        from new_phone.auth.passwords import hash_password

        user = make_user(
            id=USER_ACME_ADMIN_ID,
            password_hash=hash_password("actual-password"),
        )
        mock_db.execute.return_value = make_scalar_result(user)
        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="Current password is incorrect"):
            await service.change_password(
                USER_ACME_ADMIN_ID, "wrong-password", "new-password-123"
            )

    async def test_user_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="User not found"):
            await service.change_password(
                USER_ACME_ADMIN_ID, "any", "new-password-123"
            )

    async def test_inactive_user_raises(self, mock_db):
        user = make_user(id=USER_ACME_ADMIN_ID, is_active=False)
        mock_db.execute.return_value = make_scalar_result(user)
        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="deactivated"):
            await service.change_password(
                USER_ACME_ADMIN_ID, "any", "new-password-123"
            )

    async def test_no_password_hash_raises(self, mock_db):
        user = make_user(id=USER_ACME_ADMIN_ID, password_hash=None)
        mock_db.execute.return_value = make_scalar_result(user)
        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="not configured"):
            await service.change_password(
                USER_ACME_ADMIN_ID, "any", "new-password-123"
            )
