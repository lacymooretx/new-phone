import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.models.tenant import Tenant
from new_phone.schemas.tenant import TenantCreate, TenantUpdate

logger = structlog.get_logger()

# Plan → quota defaults
_PLAN_QUOTAS: dict[str, dict[str, int]] = {
    "trial": {"max_extensions": 10, "max_dids": 2, "max_concurrent_calls": 5},
    "starter": {"max_extensions": 25, "max_dids": 10, "max_concurrent_calls": 15},
    "professional": {"max_extensions": 100, "max_dids": 50, "max_concurrent_calls": 50},
    "enterprise": {"max_extensions": 1000, "max_dids": 500, "max_concurrent_calls": 300},
}


class TenantService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_tenants(self) -> list[Tenant]:
        result = await self.db.execute(select(Tenant).order_by(Tenant.name))
        return list(result.scalars().all())

    async def get_tenant(self, tenant_id: uuid.UUID) -> Tenant | None:
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()

    async def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        result = await self.db.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def get_tenant_by_sip_domain(self, sip_domain: str) -> Tenant | None:
        result = await self.db.execute(
            select(Tenant).where(Tenant.sip_domain == sip_domain)
        )
        return result.scalar_one_or_none()

    async def create_tenant(self, data: TenantCreate) -> Tenant:
        existing = await self.get_tenant_by_slug(data.slug)
        if existing:
            raise ValueError(f"Tenant with slug '{data.slug}' already exists")

        tenant_data = data.model_dump()
        # Auto-generate sip_domain from slug if not provided
        if not tenant_data.get("sip_domain"):
            tenant_data["sip_domain"] = f"{data.slug}.sip.local"

        tenant = Tenant(**tenant_data)
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def update_tenant(self, tenant_id: uuid.UUID, data: TenantUpdate) -> Tenant:
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(tenant, key, value)

        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def deactivate_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")

        tenant.is_active = False
        tenant.lifecycle_state = "cancelled"
        tenant.deactivated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def set_lifecycle_state(
        self, tenant_id: uuid.UUID, state: str
    ) -> Tenant:
        """Transition a tenant to a new lifecycle state."""
        valid = {"trial", "active", "suspended", "cancelled"}
        if state not in valid:
            raise ValueError(f"Invalid lifecycle state '{state}'. Must be one of: {valid}")

        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")

        tenant.lifecycle_state = state
        if state == "cancelled":
            tenant.is_active = False
            tenant.deactivated_at = datetime.now(UTC)
        elif state in ("trial", "active"):
            tenant.is_active = True
            tenant.deactivated_at = None

        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    # ------------------------------------------------------------------
    # Onboarding orchestration
    # ------------------------------------------------------------------

    async def onboard_tenant(
        self,
        *,
        name: str,
        slug: str,
        domain: str | None,
        admin_email: str,
        admin_first_name: str = "Admin",
        admin_last_name: str = "User",
        plan: str = "trial",
        provider: str = "clearlyip",
        region: str = "us-east",
        area_code: str | None = None,
        initial_did_count: int = 1,
        initial_extensions: int = 10,
    ) -> dict:
        """Full tenant onboarding orchestration.

        Steps:
        1. Create tenant with quotas
        2. Provision SIP trunk
        3. Purchase DIDs
        4. Create admin user
        5. Create default extensions

        Returns a dict summarising what was created.
        """
        from new_phone.models.user import User, UserRole
        from new_phone.services.did_service import DIDService
        from new_phone.services.sip_trunk_service import SIPTrunkService

        steps: list[dict] = []
        quotas = _PLAN_QUOTAS.get(plan, _PLAN_QUOTAS["trial"])

        # --- Step 1: Create tenant ----------------------------------
        logger.info("onboard_step_create_tenant", slug=slug, plan=plan)
        existing = await self.get_tenant_by_slug(slug)
        if existing:
            raise ValueError(f"Tenant with slug '{slug}' already exists")

        tenant = Tenant(
            name=name,
            slug=slug,
            domain=domain,
            sip_domain=f"{slug}.sip.local",
            lifecycle_state="trial" if plan == "trial" else "active",
            max_extensions=quotas["max_extensions"],
            max_dids=quotas["max_dids"],
            max_concurrent_calls=quotas["max_concurrent_calls"],
        )
        self.db.add(tenant)
        await self.db.flush()  # Get tenant.id without committing
        steps.append({"step": "create_tenant", "status": "completed"})

        # --- Step 2: Provision SIP trunk -----------------------------
        trunk_provisioned = False
        try:
            logger.info("onboard_step_provision_trunk", tenant_id=str(tenant.id))
            trunk_svc = SIPTrunkService(self.db)
            await trunk_svc.provision(
                tenant_id=tenant.id,
                provider_type=provider,
                name=f"{slug}-primary",
                region=region,
                channels=quotas["max_concurrent_calls"],
            )
            trunk_provisioned = True
            steps.append({"step": "provision_trunk", "status": "completed"})
        except Exception as exc:
            logger.warning("onboard_trunk_failed", error=str(exc))
            steps.append({
                "step": "provision_trunk",
                "status": "failed",
                "detail": str(exc),
            })

        # --- Step 3: Purchase DIDs -----------------------------------
        dids_purchased = 0
        did_svc = DIDService(self.db)
        if initial_did_count > 0:
            try:
                logger.info(
                    "onboard_step_purchase_dids",
                    tenant_id=str(tenant.id),
                    count=initial_did_count,
                )
                available = await did_svc.search_available(
                    tenant.id,
                    area_code=area_code,
                    quantity=initial_did_count,
                    provider_type=provider,
                )
                for did_result in available[:initial_did_count]:
                    try:
                        await did_svc.purchase(tenant.id, did_result.number, provider)
                        dids_purchased += 1
                    except Exception as exc:
                        logger.warning(
                            "onboard_did_purchase_failed",
                            number=did_result.number,
                            error=str(exc),
                        )
                steps.append({
                    "step": "purchase_dids",
                    "status": "completed" if dids_purchased > 0 else "failed",
                    "detail": f"{dids_purchased}/{initial_did_count} purchased",
                })
            except Exception as exc:
                logger.warning("onboard_did_search_failed", error=str(exc))
                steps.append({
                    "step": "purchase_dids",
                    "status": "failed",
                    "detail": str(exc),
                })
        else:
            steps.append({"step": "purchase_dids", "status": "completed", "detail": "0 requested"})

        # --- Step 4: Create admin user -------------------------------
        try:
            logger.info("onboard_step_create_admin", email=admin_email)

            # Check for existing user with same email
            existing_user = await self.db.execute(
                select(User).where(User.email == admin_email)
            )
            if existing_user.scalar_one_or_none():
                steps.append({
                    "step": "create_admin",
                    "status": "skipped",
                    "detail": "User with this email already exists",
                })
            else:
                import secrets

                import bcrypt

                temp_password = secrets.token_urlsafe(16)
                password_hash = bcrypt.hashpw(
                    temp_password.encode(), bcrypt.gensalt()
                ).decode()

                admin_user = User(
                    tenant_id=tenant.id,
                    email=admin_email,
                    password_hash=password_hash,
                    first_name=admin_first_name,
                    last_name=admin_last_name,
                    role=UserRole.TENANT_ADMIN,
                )
                self.db.add(admin_user)
                await self.db.flush()
                steps.append({"step": "create_admin", "status": "completed"})
        except Exception as exc:
            logger.warning("onboard_create_admin_failed", error=str(exc))
            steps.append({
                "step": "create_admin",
                "status": "failed",
                "detail": str(exc),
            })

        # --- Step 5: Create default extensions -----------------------
        extensions_created = 0
        if initial_extensions > 0:
            try:
                logger.info(
                    "onboard_step_create_extensions",
                    tenant_id=str(tenant.id),
                    count=initial_extensions,
                )
                import secrets as ext_secrets

                import bcrypt as ext_bcrypt

                from new_phone.auth.encryption import encrypt_value
                from new_phone.models.extension import Extension

                for i in range(initial_extensions):
                    ext_number = str(1000 + i)
                    sip_user = f"{slug}-{ext_number}"
                    sip_pass = ext_secrets.token_urlsafe(16)
                    sip_pass_hash = ext_bcrypt.hashpw(
                        sip_pass.encode(), ext_bcrypt.gensalt()
                    ).decode()

                    ext = Extension(
                        tenant_id=tenant.id,
                        extension_number=ext_number,
                        sip_username=sip_user,
                        sip_password_hash=sip_pass_hash,
                        encrypted_sip_password=encrypt_value(sip_pass),
                        internal_cid_name=f"Ext {ext_number}",
                        internal_cid_number=ext_number,
                    )
                    self.db.add(ext)
                    extensions_created += 1

                await self.db.flush()
                steps.append({
                    "step": "create_extensions",
                    "status": "completed",
                    "detail": f"{extensions_created} created",
                })
            except Exception as exc:
                logger.warning("onboard_extensions_failed", error=str(exc))
                steps.append({
                    "step": "create_extensions",
                    "status": "failed",
                    "detail": str(exc),
                })
        else:
            steps.append({
                "step": "create_extensions",
                "status": "completed",
                "detail": "0 requested",
            })

        # --- Commit everything ---------------------------------------
        await self.db.commit()
        await self.db.refresh(tenant)

        logger.info(
            "onboard_complete",
            tenant_id=str(tenant.id),
            slug=slug,
            trunk_provisioned=trunk_provisioned,
            dids_purchased=dids_purchased,
            extensions_created=extensions_created,
        )

        return {
            "tenant": tenant,
            "steps": steps,
            "trunk_provisioned": trunk_provisioned,
            "dids_purchased": dids_purchased,
            "extensions_created": extensions_created,
        }
