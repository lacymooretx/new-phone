import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import decrypt_value, encrypt_value
from new_phone.auth.jwt import (
    create_access_token,
    create_mfa_token,
    create_refresh_token,
    decode_token,
)
from new_phone.auth.mfa import (
    generate_qr_code,
    generate_totp_secret,
    get_provisioning_uri,
    verify_totp,
)
from new_phone.auth.passwords import hash_password, hash_token, verify_password, verify_token
from new_phone.config import settings
from new_phone.models.user import User


class AuthService:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

    async def authenticate(self, email: str, password: str) -> dict:
        """Authenticate user by email/password.

        Returns:
            - TokenResponse if no MFA
            - MFAChallengeResponse if MFA enabled
            - None if auth fails

        Raises:
            ValueError with descriptive message on failure.
        """
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("Account is deactivated")

        # Check if tenant enforces SSO
        from new_phone.models.sso_provider import SSOProvider
        sso_result = await self.db.execute(
            select(SSOProvider).where(
                SSOProvider.tenant_id == user.tenant_id,
                SSOProvider.is_active.is_(True),
                SSOProvider.enforce_sso.is_(True),
            )
        )
        if sso_result.scalar_one_or_none():
            raise ValueError("This organization requires SSO sign-in. Use the SSO button to log in.")

        # Check lockout
        if user.locked_until and user.locked_until > datetime.now(UTC):
            raise ValueError("Account is temporarily locked")

        if not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.max_failed_login_attempts:
                user.locked_until = datetime.now(UTC) + timedelta(
                    minutes=settings.lockout_duration_minutes
                )
            await self.db.commit()
            raise ValueError("Invalid email or password")

        # Reset failed attempts on success
        user.failed_login_attempts = 0
        user.locked_until = None

        # If MFA enabled, return MFA challenge
        if user.mfa_enabled:
            mfa_token = create_mfa_token(user.id)
            await self.db.commit()
            return {"mfa_required": True, "mfa_token": mfa_token}

        # No MFA — issue tokens
        return await self._issue_tokens(user)

    async def complete_mfa_challenge(self, mfa_token: str, code: str) -> dict:
        """Complete MFA challenge with TOTP code."""
        payload = decode_token(mfa_token)
        if payload.get("type") != "mfa_pending":
            raise ValueError("Invalid MFA token")

        user_id = uuid.UUID(payload["sub"])
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.mfa_secret:
            raise ValueError("Invalid MFA token")

        decrypted = decrypt_value(user.mfa_secret)
        if not verify_totp(decrypted, code):
            raise ValueError("Invalid MFA code")

        return await self._issue_tokens(user)

    async def refresh_tokens(self, refresh_token: str) -> dict:
        """Rotate refresh token and issue new token pair."""
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Invalid refresh token")

        user_id = uuid.UUID(payload["sub"])
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        # Verify the refresh token matches the stored hash
        if not user.refresh_token_hash or not verify_token(
            refresh_token, user.refresh_token_hash
        ):
            raise ValueError("Invalid refresh token")

        # Redis-based rotation detection: if the hash in Redis differs, the token
        # was already rotated — this is token reuse, so invalidate everything.
        if self.redis:
            redis_key = f"refresh_token:{user_id}"
            stored_hash = await self.redis.get(redis_key)
            current_hash = hash_token(refresh_token)
            if stored_hash and stored_hash != current_hash:
                # Token reuse detected — invalidate all tokens for this user
                await self.redis.delete(redis_key)
                user.refresh_token_hash = None
                user.refresh_token_expires_at = None
                await self.db.commit()
                raise ValueError("Token reuse detected — all sessions invalidated")

        return await self._issue_tokens(user)

    async def setup_mfa(self, user: User) -> dict:
        """Generate TOTP secret and QR code for MFA setup."""
        secret = generate_totp_secret()
        provisioning_uri = get_provisioning_uri(secret, user.email)
        qr_code = generate_qr_code(provisioning_uri)

        # Store encrypted secret — don't enable MFA yet (need verify step)
        user.mfa_secret = encrypt_value(secret)
        await self.db.commit()

        return {
            "secret": secret,
            "qr_code": qr_code,
            "provisioning_uri": provisioning_uri,
        }

    async def verify_mfa_setup(self, user: User, code: str) -> bool:
        """Verify TOTP code to confirm MFA setup."""
        if not user.mfa_secret:
            raise ValueError("MFA not set up")

        decrypted = decrypt_value(user.mfa_secret)
        if not verify_totp(decrypted, code):
            raise ValueError("Invalid code")

        user.mfa_enabled = True
        await self.db.commit()
        return True

    async def change_password(
        self, user_id: uuid.UUID, current_password: str, new_password: str
    ) -> bool:
        """Change a user's password after verifying the current one.

        Raises:
            ValueError with descriptive message on failure.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        if not user.is_active:
            raise ValueError("Account is deactivated")

        if not user.password_hash:
            raise ValueError("Password login is not configured for this account")

        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")

        user.password_hash = hash_password(new_password)
        await self.db.commit()
        return True

    async def _issue_tokens(self, user: User) -> dict:
        """Issue access + refresh token pair."""
        access_token = create_access_token(user.id, user.tenant_id, user.role, user.language)
        refresh_token, expires_at = create_refresh_token(user.id)

        token_hash = hash_token(refresh_token)
        user.refresh_token_hash = token_hash
        user.refresh_token_expires_at = expires_at
        user.last_login_at = datetime.now(UTC)
        await self.db.commit()

        # Store refresh token hash in Redis for rotation detection
        if self.redis:
            redis_key = f"refresh_token:{user.id}"
            ttl = settings.jwt_refresh_token_expire_days * 86400
            await self.redis.set(redis_key, token_hash, ex=ttl)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
