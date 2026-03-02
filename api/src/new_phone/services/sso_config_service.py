import uuid

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import encrypt_value
from new_phone.models.sso_provider import SSOProvider
from new_phone.models.sso_role_mapping import SSORoleMapping
from new_phone.schemas.sso import SSOProviderCreate, SSOProviderUpdate

logger = structlog.get_logger()

DISCOVERY_URL_TEMPLATES = {
    "microsoft": "{issuer_url}/.well-known/openid-configuration",
    "google": "https://accounts.google.com/.well-known/openid-configuration",
}


class SSOConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_provider(self, tenant_id: uuid.UUID) -> SSOProvider | None:
        result = await self.db.execute(
            select(SSOProvider).where(SSOProvider.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create_provider(
        self, tenant_id: uuid.UUID, data: SSOProviderCreate
    ) -> SSOProvider:
        existing = await self.get_provider(tenant_id)
        if existing:
            raise ValueError("SSO provider already configured for this tenant")

        discovery_url = self._build_discovery_url(data.provider_type, data.issuer_url)

        provider = SSOProvider(
            tenant_id=tenant_id,
            provider_type=data.provider_type,
            display_name=data.display_name,
            client_id=data.client_id,
            client_secret_encrypted=encrypt_value(data.client_secret),
            issuer_url=data.issuer_url,
            discovery_url=discovery_url,
            scopes=data.scopes,
            auto_provision=data.auto_provision,
            default_role=data.default_role,
            enforce_sso=data.enforce_sso,
        )
        self.db.add(provider)
        await self.db.commit()
        await self.db.refresh(provider)
        return provider

    async def update_provider(
        self, provider_id: uuid.UUID, data: SSOProviderUpdate
    ) -> SSOProvider:
        result = await self.db.execute(
            select(SSOProvider).where(SSOProvider.id == provider_id)
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise ValueError("SSO provider not found")

        update_data = data.model_dump(exclude_unset=True)

        client_secret = update_data.pop("client_secret", None)
        if client_secret:
            provider.client_secret_encrypted = encrypt_value(client_secret)

        if "issuer_url" in update_data:
            provider.discovery_url = self._build_discovery_url(
                provider.provider_type, update_data["issuer_url"]
            )

        for key, value in update_data.items():
            setattr(provider, key, value)

        await self.db.commit()
        await self.db.refresh(provider)
        return provider

    async def delete_provider(self, provider_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(SSOProvider).where(SSOProvider.id == provider_id)
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise ValueError("SSO provider not found")

        await self.db.delete(provider)
        await self.db.commit()

    async def add_role_mapping(
        self, provider_id: uuid.UUID, external_group_id: str,
        external_group_name: str | None, pbx_role: str,
    ) -> SSORoleMapping:
        mapping = SSORoleMapping(
            sso_provider_id=provider_id,
            external_group_id=external_group_id,
            external_group_name=external_group_name,
            pbx_role=pbx_role,
        )
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping

    async def remove_role_mapping(self, mapping_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(SSORoleMapping).where(SSORoleMapping.id == mapping_id)
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            raise ValueError("Role mapping not found")
        await self.db.delete(mapping)
        await self.db.commit()

    async def list_role_mappings(self, provider_id: uuid.UUID) -> list[SSORoleMapping]:
        result = await self.db.execute(
            select(SSORoleMapping)
            .where(SSORoleMapping.sso_provider_id == provider_id)
            .order_by(SSORoleMapping.external_group_name)
        )
        return list(result.scalars().all())

    async def test_connection(self, provider_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(SSOProvider).where(SSOProvider.id == provider_id)
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise ValueError("SSO provider not found")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(provider.discovery_url)
                resp.raise_for_status()
                discovery = resp.json()

            required_keys = {"authorization_endpoint", "token_endpoint", "jwks_uri", "issuer"}
            missing = required_keys - set(discovery.keys())
            if missing:
                return {"success": False, "message": f"Discovery doc missing keys: {', '.join(missing)}"}

            return {"success": True, "message": "OIDC discovery document validated successfully"}
        except httpx.HTTPStatusError as e:
            return {"success": False, "message": f"HTTP {e.response.status_code} fetching discovery document"}
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {e!s}"}

    def _build_discovery_url(self, provider_type: str, issuer_url: str) -> str:
        if provider_type == "google":
            return DISCOVERY_URL_TEMPLATES["google"]
        # Microsoft: append .well-known path to issuer URL
        issuer = issuer_url.rstrip("/")
        return f"{issuer}/.well-known/openid-configuration"
