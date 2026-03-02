import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.ten_dlc import Brand, Campaign, ComplianceDocument
from new_phone.schemas.ten_dlc import BrandCreate, BrandUpdate, CampaignCreate, CampaignUpdate

logger = structlog.get_logger()


class TenDLCService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Brand CRUD ─────────────────────────────────────────────────────

    async def create_brand(self, tenant_id: uuid.UUID, data: BrandCreate) -> Brand:
        await set_tenant_context(self.db, tenant_id)
        brand = Brand(
            tenant_id=tenant_id,
            name=data.name,
            ein=data.ein,
            ein_issuing_country=data.ein_issuing_country,
            brand_type=data.brand_type,
            vertical=data.vertical,
            website=data.website,
            status="draft",
        )
        self.db.add(brand)
        await self.db.commit()
        await self.db.refresh(brand)
        logger.info("ten_dlc_brand_created", brand_id=str(brand.id), tenant_id=str(tenant_id))
        return brand

    async def list_brands(self, tenant_id: uuid.UUID) -> list[Brand]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Brand)
            .where(Brand.tenant_id == tenant_id, Brand.is_active.is_(True))
            .order_by(Brand.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_brand(self, tenant_id: uuid.UUID, brand_id: uuid.UUID) -> Brand | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Brand).where(Brand.id == brand_id, Brand.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update_brand(self, tenant_id: uuid.UUID, brand_id: uuid.UUID, data: BrandUpdate) -> Brand:
        await set_tenant_context(self.db, tenant_id)
        brand = await self.get_brand(tenant_id, brand_id)
        if not brand:
            raise ValueError("Brand not found")
        if brand.status not in ("draft", "rejected"):
            raise ValueError(f"Cannot update brand in '{brand.status}' status")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(brand, field, value)

        await self.db.commit()
        await self.db.refresh(brand)
        logger.info("ten_dlc_brand_updated", brand_id=str(brand_id))
        return brand

    async def register_brand(self, tenant_id: uuid.UUID, brand_id: uuid.UUID) -> Brand:
        """Submit a brand for registration with the SMS provider's 10DLC API."""
        await set_tenant_context(self.db, tenant_id)
        brand = await self.get_brand(tenant_id, brand_id)
        if not brand:
            raise ValueError("Brand not found")
        if brand.status not in ("draft", "rejected"):
            raise ValueError(f"Cannot register brand in '{brand.status}' status")

        # Attempt registration via SMS provider's 10DLC API
        try:
            from new_phone.sms.factory import get_tenant_default_provider

            config, provider = await get_tenant_default_provider(self.db, tenant_id)

            # Build brand registration payload
            brand_payload = {
                "name": brand.name,
                "ein": brand.ein,
                "ein_issuing_country": brand.ein_issuing_country,
                "brand_type": brand.brand_type,
                "vertical": brand.vertical,
                "website": brand.website,
            }

            # Call provider-specific 10DLC brand registration
            # Providers that support 10DLC will have this method; others will raise
            if hasattr(provider, "register_brand"):
                result = await provider.register_brand(brand_payload)
                brand.provider_brand_id = result.get("brand_id", "")
                brand.status = "pending"
            else:
                # Provider does not support programmatic 10DLC registration
                # Mark as pending — admin will complete registration externally
                brand.status = "pending"
                logger.info(
                    "ten_dlc_brand_register_manual",
                    brand_id=str(brand_id),
                    provider=config.provider_type,
                )

            brand.submitted_at = datetime.now(UTC)
        except ValueError:
            # No default provider configured — still allow marking as pending
            brand.status = "pending"
            brand.submitted_at = datetime.now(UTC)
            logger.warning("ten_dlc_brand_register_no_provider", brand_id=str(brand_id))
        except Exception as e:
            logger.error("ten_dlc_brand_register_failed", brand_id=str(brand_id), error=str(e))
            raise ValueError(f"Brand registration failed: {e}") from e

        await self.db.commit()
        await self.db.refresh(brand)
        logger.info("ten_dlc_brand_registered", brand_id=str(brand_id), status=brand.status)
        return brand

    async def check_brand_status(self, tenant_id: uuid.UUID, brand_id: uuid.UUID) -> Brand:
        """Poll the provider for current brand registration status."""
        await set_tenant_context(self.db, tenant_id)
        brand = await self.get_brand(tenant_id, brand_id)
        if not brand:
            raise ValueError("Brand not found")

        if brand.status != "pending":
            return brand

        if not brand.provider_brand_id:
            # No provider ID — cannot poll; return current state
            return brand

        try:
            from new_phone.sms.factory import get_tenant_default_provider

            _config, provider = await get_tenant_default_provider(self.db, tenant_id)

            if hasattr(provider, "check_brand_status"):
                result = await provider.check_brand_status(brand.provider_brand_id)
                new_status = result.get("status", "").lower()

                if new_status == "approved":
                    brand.status = "approved"
                    brand.approved_at = datetime.now(UTC)
                    brand.rejection_reason = None
                elif new_status == "rejected":
                    brand.status = "rejected"
                    brand.rejection_reason = result.get("reason", "Rejected by carrier")
                # else: still pending, no change

                await self.db.commit()
                await self.db.refresh(brand)
        except Exception as e:
            logger.warning("ten_dlc_brand_status_check_failed", brand_id=str(brand_id), error=str(e))

        return brand

    # ── Campaign CRUD ──────────────────────────────────────────────────

    async def create_campaign(self, tenant_id: uuid.UUID, data: CampaignCreate) -> Campaign:
        await set_tenant_context(self.db, tenant_id)

        # Verify the brand exists and belongs to this tenant
        brand = await self.get_brand(tenant_id, data.brand_id)
        if not brand:
            raise ValueError("Brand not found")

        campaign = Campaign(
            tenant_id=tenant_id,
            brand_id=data.brand_id,
            name=data.name,
            use_case=data.use_case,
            description=data.description,
            sample_messages=data.sample_messages,
            message_flow=data.message_flow,
            help_message=data.help_message,
            opt_out_message=data.opt_out_message,
            opt_in_keywords=data.opt_in_keywords,
            opt_out_keywords=data.opt_out_keywords,
            help_keywords=data.help_keywords,
            number_pool=data.number_pool,
            status="draft",
        )
        self.db.add(campaign)
        await self.db.commit()
        await self.db.refresh(campaign)
        logger.info("ten_dlc_campaign_created", campaign_id=str(campaign.id), tenant_id=str(tenant_id))
        return campaign

    async def list_campaigns(
        self, tenant_id: uuid.UUID, brand_id: uuid.UUID | None = None
    ) -> list[Campaign]:
        await set_tenant_context(self.db, tenant_id)
        query = select(Campaign).where(
            Campaign.tenant_id == tenant_id, Campaign.is_active.is_(True)
        )
        if brand_id:
            query = query.where(Campaign.brand_id == brand_id)
        query = query.order_by(Campaign.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_campaign(self, tenant_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update_campaign(
        self, tenant_id: uuid.UUID, campaign_id: uuid.UUID, data: CampaignUpdate
    ) -> Campaign:
        await set_tenant_context(self.db, tenant_id)
        campaign = await self.get_campaign(tenant_id, campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")
        if campaign.status not in ("draft", "rejected"):
            raise ValueError(f"Cannot update campaign in '{campaign.status}' status")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(campaign, field, value)

        await self.db.commit()
        await self.db.refresh(campaign)
        logger.info("ten_dlc_campaign_updated", campaign_id=str(campaign_id))
        return campaign

    async def register_campaign(self, tenant_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign:
        """Submit a campaign for registration with the SMS provider's 10DLC API."""
        await set_tenant_context(self.db, tenant_id)
        campaign = await self.get_campaign(tenant_id, campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")
        if campaign.status not in ("draft", "rejected"):
            raise ValueError(f"Cannot register campaign in '{campaign.status}' status")

        # Verify associated brand is approved
        brand = await self.get_brand(tenant_id, campaign.brand_id)
        if not brand or brand.status != "approved":
            raise ValueError("Associated brand must be approved before registering a campaign")

        try:
            from new_phone.sms.factory import get_tenant_default_provider

            config, provider = await get_tenant_default_provider(self.db, tenant_id)

            campaign_payload = {
                "brand_id": brand.provider_brand_id,
                "name": campaign.name,
                "use_case": campaign.use_case,
                "description": campaign.description,
                "sample_messages": campaign.sample_messages,
                "message_flow": campaign.message_flow,
                "help_message": campaign.help_message,
                "opt_out_message": campaign.opt_out_message,
                "opt_in_keywords": campaign.opt_in_keywords,
                "opt_out_keywords": campaign.opt_out_keywords,
                "help_keywords": campaign.help_keywords,
                "number_pool": campaign.number_pool,
            }

            if hasattr(provider, "register_campaign"):
                result = await provider.register_campaign(campaign_payload)
                campaign.provider_campaign_id = result.get("campaign_id", "")
                campaign.status = "pending"
            else:
                campaign.status = "pending"
                logger.info(
                    "ten_dlc_campaign_register_manual",
                    campaign_id=str(campaign_id),
                    provider=config.provider_type,
                )

            campaign.submitted_at = datetime.now(UTC)
        except ValueError:
            campaign.status = "pending"
            campaign.submitted_at = datetime.now(UTC)
            logger.warning("ten_dlc_campaign_register_no_provider", campaign_id=str(campaign_id))
        except Exception as e:
            logger.error("ten_dlc_campaign_register_failed", campaign_id=str(campaign_id), error=str(e))
            raise ValueError(f"Campaign registration failed: {e}") from e

        await self.db.commit()
        await self.db.refresh(campaign)
        logger.info("ten_dlc_campaign_registered", campaign_id=str(campaign_id), status=campaign.status)
        return campaign

    async def check_campaign_status(self, tenant_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign:
        """Poll the provider for current campaign registration status."""
        await set_tenant_context(self.db, tenant_id)
        campaign = await self.get_campaign(tenant_id, campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")

        if campaign.status != "pending":
            return campaign

        if not campaign.provider_campaign_id:
            return campaign

        try:
            from new_phone.sms.factory import get_tenant_default_provider

            _config, provider = await get_tenant_default_provider(self.db, tenant_id)

            if hasattr(provider, "check_campaign_status"):
                result = await provider.check_campaign_status(campaign.provider_campaign_id)
                new_status = result.get("status", "").lower()

                if new_status == "approved":
                    campaign.status = "approved"
                    campaign.approved_at = datetime.now(UTC)
                    campaign.rejection_reason = None
                elif new_status == "rejected":
                    campaign.status = "rejected"
                    campaign.rejection_reason = result.get("reason", "Rejected by carrier")
                elif new_status == "suspended":
                    campaign.status = "suspended"
                    campaign.rejection_reason = result.get("reason", "Suspended by carrier")

                await self.db.commit()
                await self.db.refresh(campaign)
        except Exception as e:
            logger.warning(
                "ten_dlc_campaign_status_check_failed", campaign_id=str(campaign_id), error=str(e)
            )

        return campaign

    # ── Compliance Documents ───────────────────────────────────────────

    async def upload_compliance_doc(
        self,
        tenant_id: uuid.UUID,
        brand_id: uuid.UUID,
        document_type: str,
        file_path: str,
        original_filename: str,
    ) -> ComplianceDocument:
        await set_tenant_context(self.db, tenant_id)

        # Verify brand exists
        brand = await self.get_brand(tenant_id, brand_id)
        if not brand:
            raise ValueError("Brand not found")

        doc = ComplianceDocument(
            tenant_id=tenant_id,
            brand_id=brand_id,
            document_type=document_type,
            file_path=file_path,
            original_filename=original_filename,
            uploaded_at=datetime.now(UTC),
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        logger.info(
            "ten_dlc_compliance_doc_uploaded",
            doc_id=str(doc.id),
            brand_id=str(brand_id),
            document_type=document_type,
        )
        return doc

    async def list_compliance_docs(
        self, tenant_id: uuid.UUID, brand_id: uuid.UUID
    ) -> list[ComplianceDocument]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(ComplianceDocument)
            .where(
                ComplianceDocument.tenant_id == tenant_id,
                ComplianceDocument.brand_id == brand_id,
                ComplianceDocument.is_active.is_(True),
            )
            .order_by(ComplianceDocument.uploaded_at.desc())
        )
        return list(result.scalars().all())
