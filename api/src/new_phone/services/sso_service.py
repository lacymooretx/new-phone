import base64
import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime

import httpx
import structlog
from jose import JWTError
from jose import jwt as jose_jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import decrypt_value
from new_phone.auth.jwt import create_access_token, create_refresh_token
from new_phone.auth.passwords import hash_token
from new_phone.config import settings
from new_phone.models.sso_provider import SSOProvider
from new_phone.models.sso_role_mapping import SSORoleMapping
from new_phone.models.tenant import Tenant
from new_phone.models.user import User, UserRole
from new_phone.models.user_sso_link import UserSSOLink

logger = structlog.get_logger()


class SSOService:
    def __init__(self, db: AsyncSession, redis):
        self.db = db
        self.redis = redis

    async def check_domain(self, email: str) -> dict:
        """Check if an email domain has SSO configured."""
        domain = email.split("@")[1].lower() if "@" in email else ""
        if not domain:
            return {"sso_available": False, "provider_type": None, "display_name": None, "enforce_sso": False}

        result = await self.db.execute(
            select(Tenant).where(Tenant.domain == domain, Tenant.is_active.is_(True))
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return {"sso_available": False, "provider_type": None, "display_name": None, "enforce_sso": False}

        result = await self.db.execute(
            select(SSOProvider).where(
                SSOProvider.tenant_id == tenant.id,
                SSOProvider.is_active.is_(True),
            )
        )
        provider = result.scalar_one_or_none()
        if not provider:
            return {"sso_available": False, "provider_type": None, "display_name": None, "enforce_sso": False}

        return {
            "sso_available": True,
            "provider_type": provider.provider_type,
            "display_name": provider.display_name,
            "enforce_sso": provider.enforce_sso,
        }

    async def initiate_sso(self, email: str) -> dict:
        """Start the SSO flow — generate state, nonce, PKCE, build auth URL."""
        domain = email.split("@")[1].lower() if "@" in email else ""
        if not domain:
            raise ValueError("Invalid email address")

        result = await self.db.execute(
            select(Tenant).where(Tenant.domain == domain, Tenant.is_active.is_(True))
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ValueError("No tenant found for this domain")

        result = await self.db.execute(
            select(SSOProvider).where(
                SSOProvider.tenant_id == tenant.id,
                SSOProvider.is_active.is_(True),
            )
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise ValueError("SSO not configured for this domain")

        # Fetch OIDC discovery document (cached in Redis)
        discovery = await self._get_discovery(provider)

        # Generate PKCE
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()

        # Generate state and nonce
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        # Store state in Redis
        state_data = {
            "nonce": nonce,
            "code_verifier": code_verifier,
            "provider_id": str(provider.id),
            "tenant_id": str(tenant.id),
            "email": email,
        }
        await self.redis.setex(
            f"sso:state:{state}",
            settings.sso_state_ttl_seconds,
            json.dumps(state_data),
        )

        # Build authorization URL
        auth_endpoint = discovery["authorization_endpoint"]
        params = {
            "response_type": "code",
            "client_id": provider.client_id,
            "redirect_uri": settings.sso_callback_url,
            "scope": provider.scopes,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        # For Microsoft, add prompt=select_account
        if provider.provider_type == "microsoft":
            params["prompt"] = "select_account"

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        authorization_url = f"{auth_endpoint}?{query_string}"

        return {"authorization_url": authorization_url, "state": state}

    async def handle_callback(self, code: str, state: str) -> str:
        """Handle the OIDC callback — exchange code, validate token, provision user.

        Returns the state key that can be used to retrieve tokens.
        """
        # Retrieve and delete state (one-time use)
        state_key = f"sso:state:{state}"
        state_json = await self.redis.get(state_key)
        if not state_json:
            raise ValueError("Invalid or expired SSO state")
        await self.redis.delete(state_key)

        state_data = json.loads(state_json)
        provider_id = uuid.UUID(state_data["provider_id"])
        tenant_id = uuid.UUID(state_data["tenant_id"])
        nonce = state_data["nonce"]
        code_verifier = state_data["code_verifier"]

        # Load provider
        result = await self.db.execute(
            select(SSOProvider).where(SSOProvider.id == provider_id)
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise ValueError("SSO provider not found")

        # Get discovery doc
        discovery = await self._get_discovery(provider)

        # Exchange authorization code for tokens
        client_secret = decrypt_value(provider.client_secret_encrypted)
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                discovery["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.sso_callback_url,
                    "client_id": provider.client_id,
                    "client_secret": client_secret,
                    "code_verifier": code_verifier,
                },
            )
            if token_resp.status_code != 200:
                logger.error("sso_token_exchange_failed", status=token_resp.status_code, body=token_resp.text[:500])
                raise ValueError("Failed to exchange authorization code")
            token_data = token_resp.json()

        id_token = token_data.get("id_token")
        if not id_token:
            raise ValueError("No ID token in response")

        # Validate ID token
        claims = await self._validate_id_token(id_token, provider, discovery, nonce)

        # Extract user info from claims
        sub = claims.get("sub")
        email = claims.get("email", "").lower()
        given_name = claims.get("given_name", "")
        family_name = claims.get("family_name", "")
        name = claims.get("name", "")
        groups = claims.get("groups", [])

        if not sub or not email:
            raise ValueError("ID token missing required claims (sub, email)")

        # If name fields are missing, try to split the 'name' claim
        if not given_name and name:
            parts = name.split(" ", 1)
            given_name = parts[0]
            family_name = parts[1] if len(parts) > 1 else ""

        # User resolution / JIT provisioning
        user = await self._resolve_user(
            provider, tenant_id, sub, email, given_name or "User", family_name or ""
        )

        # Role mapping from groups
        if groups:
            await self._apply_role_mapping(provider.id, user, groups)

        # Issue JWT tokens
        tokens = await self._issue_tokens(user)

        # Store tokens in Redis for frontend retrieval (60s TTL)
        result_key = f"sso:result:{state}"
        await self.redis.setex(result_key, 60, json.dumps(tokens))

        return state

    async def complete_sso(self, state: str) -> dict:
        """Frontend calls this to retrieve tokens after SSO callback."""
        result_key = f"sso:result:{state}"
        result_json = await self.redis.get(result_key)
        if not result_json:
            raise ValueError("Invalid or expired SSO state")
        await self.redis.delete(result_key)
        return json.loads(result_json)

    # -- Private helpers -------------------------------------------------------

    async def _get_discovery(self, provider: SSOProvider) -> dict:
        """Fetch OIDC discovery document with Redis caching (1hr TTL)."""
        cache_key = f"sso:discovery:{provider.id}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(provider.discovery_url)
            resp.raise_for_status()
            discovery = resp.json()

        await self.redis.setex(cache_key, 3600, json.dumps(discovery))
        return discovery

    async def _validate_id_token(
        self, id_token: str, provider: SSOProvider, discovery: dict, nonce: str
    ) -> dict:
        """Validate ID token signature, issuer, audience, nonce, expiry."""
        jwks_uri = discovery["jwks_uri"]

        # Fetch JWKS (cached in Redis)
        jwks_cache_key = f"sso:jwks:{provider.id}"
        jwks_json = await self.redis.get(jwks_cache_key)
        if jwks_json:
            jwks = json.loads(jwks_json)
        else:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(jwks_uri)
                resp.raise_for_status()
                jwks = resp.json()
            await self.redis.setex(jwks_cache_key, 3600, json.dumps(jwks))

        # Decode the token header to get the key ID
        header = jose_jwt.get_unverified_header(id_token)
        kid = header.get("kid")

        # Find the matching key
        matching_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                matching_key = key
                break

        if not matching_key:
            # Clear cache and retry once
            await self.redis.delete(jwks_cache_key)
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(jwks_uri)
                resp.raise_for_status()
                jwks = resp.json()
            await self.redis.setex(jwks_cache_key, 3600, json.dumps(jwks))
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    matching_key = key
                    break

        if not matching_key:
            raise ValueError("No matching signing key found in JWKS")

        try:
            claims = jose_jwt.decode(
                id_token,
                matching_key,
                algorithms=["RS256"],
                audience=provider.client_id,
                issuer=discovery["issuer"],
                options={"verify_at_hash": False},
            )
        except JWTError as e:
            raise ValueError(f"ID token validation failed: {e!s}") from e

        # Verify nonce
        if claims.get("nonce") != nonce:
            raise ValueError("ID token nonce mismatch")

        return claims

    async def _resolve_user(
        self,
        provider: SSOProvider,
        tenant_id: uuid.UUID,
        sub: str,
        email: str,
        first_name: str,
        last_name: str,
    ) -> User:
        """Find or create user based on SSO identity."""
        # Check for existing SSO link
        result = await self.db.execute(
            select(UserSSOLink).where(
                UserSSOLink.sso_provider_id == provider.id,
                UserSSOLink.external_user_id == sub,
            )
        )
        sso_link = result.scalar_one_or_none()

        if sso_link:
            # Existing linked user — load and update last login
            result = await self.db.execute(
                select(User).where(User.id == sso_link.user_id)
            )
            user = result.scalar_one()
            sso_link.last_sso_login_at = datetime.now(UTC)
            sso_link.external_email = email  # update in case it changed
            return user

        # No link — check if user exists by email in this tenant
        result = await self.db.execute(
            select(User).where(
                User.email == email,
                User.tenant_id == tenant_id,
            )
        )
        user = result.scalar_one_or_none()

        if user:
            # Existing user, create SSO link
            auth_method = f"sso_{provider.provider_type}"
            user.auth_method = auth_method
            link = UserSSOLink(
                user_id=user.id,
                sso_provider_id=provider.id,
                external_user_id=sub,
                external_email=email,
                last_sso_login_at=datetime.now(UTC),
            )
            self.db.add(link)
            await self.db.flush()
            return user

        # No existing user — JIT provision if enabled
        if not provider.auto_provision:
            raise ValueError("User not found and auto-provisioning is disabled")

        auth_method = f"sso_{provider.provider_type}"
        new_user = User(
            tenant_id=tenant_id,
            email=email,
            password_hash=None,  # SSO users have no local password
            first_name=first_name,
            last_name=last_name,
            role=provider.default_role,
            auth_method=auth_method,
            is_active=True,
        )
        self.db.add(new_user)
        await self.db.flush()

        link = UserSSOLink(
            user_id=new_user.id,
            sso_provider_id=provider.id,
            external_user_id=sub,
            external_email=email,
            last_sso_login_at=datetime.now(UTC),
        )
        self.db.add(link)
        await self.db.flush()

        logger.info("sso_user_provisioned", user_id=str(new_user.id), email=email, tenant_id=str(tenant_id))
        return new_user

    async def _apply_role_mapping(
        self, provider_id: uuid.UUID, user: User, groups: list[str]
    ) -> None:
        """Map IdP groups to PBX roles and update user if matched."""
        result = await self.db.execute(
            select(SSORoleMapping).where(SSORoleMapping.sso_provider_id == provider_id)
        )
        mappings = {m.external_group_id: m.pbx_role for m in result.scalars().all()}

        if not mappings:
            return

        # Find the highest-privilege matching role
        role_priority = {
            UserRole.TENANT_ADMIN: 3,
            UserRole.TENANT_MANAGER: 2,
            UserRole.TENANT_USER: 1,
        }

        best_role = None
        best_priority = 0
        for group_id in groups:
            if group_id in mappings:
                role = mappings[group_id]
                priority = role_priority.get(role, 0)
                if priority > best_priority:
                    best_priority = priority
                    best_role = role

        if best_role and best_role != user.role:
            user.role = best_role
            logger.info("sso_role_updated", user_id=str(user.id), new_role=best_role)

    async def _issue_tokens(self, user: User) -> dict:
        """Issue JWT access + refresh tokens for the SSO user."""
        access_token = create_access_token(user.id, user.tenant_id, user.role, user.language)
        refresh_token, expires_at = create_refresh_token(user.id)

        user.refresh_token_hash = hash_token(refresh_token)
        user.refresh_token_expires_at = expires_at
        user.last_login_at = datetime.now(UTC)
        await self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
