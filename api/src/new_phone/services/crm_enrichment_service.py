"""CRM enrichment service — looks up phone numbers in CRM and updates CDRs."""

import asyncio
import json
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.integrations.crm.factory import get_crm_provider
from new_phone.models.cdr import CallDetailRecord
from new_phone.models.crm_config import CRMConfig

logger = structlog.get_logger()


class CRMEnrichmentService:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

    async def enrich_cdr(self, tenant_id: uuid.UUID, cdr_id: uuid.UUID) -> None:
        """Main entry point — enrich a CDR with CRM contact data. Never raises."""
        try:
            await self._do_enrich(tenant_id, cdr_id)
        except Exception as e:
            logger.error(
                "crm_enrichment_error",
                error=str(e),
                tenant_id=str(tenant_id),
                cdr_id=str(cdr_id),
            )

    async def _do_enrich(self, tenant_id: uuid.UUID, cdr_id: uuid.UUID) -> None:
        # Load CRM config
        result = await self.db.execute(
            select(CRMConfig).where(
                CRMConfig.tenant_id == tenant_id,
                CRMConfig.is_active.is_(True),
            )
        )
        config = result.scalar_one_or_none()
        if not config or not config.enrichment_enabled:
            return

        # Load CDR
        cdr_result = await self.db.execute(
            select(CallDetailRecord).where(CallDetailRecord.id == cdr_id)
        )
        cdr = cdr_result.scalar_one_or_none()
        if not cdr:
            logger.warning("crm_enrich_cdr_not_found", cdr_id=str(cdr_id))
            return

        # Check direction filtering
        if cdr.direction == "inbound" and not config.enrich_inbound:
            return
        if cdr.direction == "outbound" and not config.enrich_outbound:
            return

        # Determine lookup number
        if cdr.direction == "inbound":
            phone = cdr.caller_number
        elif cdr.direction == "outbound":
            phone = cdr.called_number
        else:
            # Internal calls — try caller
            phone = cdr.caller_number

        if not phone:
            return

        # Check Redis cache
        cache_key = f"crm:{tenant_id}:{phone}"
        cached = None
        if self.redis:
            cached = await self.redis.get(cache_key)

        if cached is not None:
            # Cache hit
            contact_data = json.loads(cached)
            if not contact_data:
                # Negative cache — no match found previously
                return
        else:
            # Cache miss — call provider
            provider = get_crm_provider(config)
            try:
                contact = await asyncio.wait_for(
                    provider.lookup_by_phone(phone),
                    timeout=config.lookup_timeout_seconds,
                )
            except TimeoutError:
                logger.warning("crm_lookup_timeout", phone=phone, provider=config.provider_type)
                return
            except Exception as e:
                logger.warning(
                    "crm_lookup_error",
                    error=str(e),
                    phone=phone,
                    provider=config.provider_type,
                )
                return
            finally:
                await provider.close()

            # Cache result (positive or negative)
            if contact:
                contact_data = {
                    "customer_name": contact.customer_name,
                    "company_name": contact.company_name,
                    "account_number": contact.account_number,
                    "account_status": contact.account_status,
                    "contact_id": contact.contact_id,
                    "deep_link_url": contact.deep_link_url,
                    "custom_fields": contact.custom_fields,
                }
            else:
                contact_data = {}

            if self.redis:
                await self.redis.set(
                    cache_key,
                    json.dumps(contact_data),
                    ex=config.cache_ttl_seconds,
                )

            if not contact_data:
                return

        # Apply enrichment to CDR
        cdr.crm_customer_name = contact_data.get("customer_name", "")[:255] or None
        cdr.crm_company_name = contact_data.get("company_name", "")[:255] or None
        cdr.crm_account_number = contact_data.get("account_number", "")[:100] or None
        cdr.crm_account_status = contact_data.get("account_status", "")[:50] or None
        cdr.crm_contact_id = contact_data.get("contact_id", "")[:255] or None
        cdr.crm_provider_type = config.provider_type
        cdr.crm_deep_link_url = contact_data.get("deep_link_url", "")[:1000] or None
        cdr.crm_custom_fields = contact_data.get("custom_fields") or None
        cdr.crm_matched_at = datetime.now(UTC)

        await self.db.commit()
        logger.info(
            "crm_enrichment_applied",
            cdr_id=str(cdr_id),
            customer=cdr.crm_customer_name,
            company=cdr.crm_company_name,
            provider=config.provider_type,
        )
