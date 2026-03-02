"""ConnectWise Manage integration service — business logic layer."""

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import decrypt_value, encrypt_value
from new_phone.integrations.connectwise_client import ConnectWiseClient
from new_phone.models.cdr import CallDetailRecord
from new_phone.models.cw_company_mapping import CWCompanyMapping
from new_phone.models.cw_config import CWConfig
from new_phone.models.cw_ticket_log import CWTicketLog
from new_phone.schemas.connectwise import (
    CWCompanyMappingCreate,
    CWConfigCreate,
    CWConfigUpdate,
)

logger = structlog.get_logger()


class ConnectWiseService:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

    # ── Config CRUD ────────────────────────────────────────────

    async def get_config(self, tenant_id: uuid.UUID) -> CWConfig | None:
        result = await self.db.execute(
            select(CWConfig).where(CWConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create_config(self, tenant_id: uuid.UUID, data: CWConfigCreate) -> CWConfig:
        existing = await self.get_config(tenant_id)
        if existing:
            raise ValueError("ConnectWise already configured for this tenant")

        config = CWConfig(
            tenant_id=tenant_id,
            company_id=data.company_id,
            public_key_encrypted=encrypt_value(data.public_key),
            private_key_encrypted=encrypt_value(data.private_key),
            client_id=data.client_id,
            base_url=data.base_url,
            api_version=data.api_version,
            default_board_id=data.default_board_id,
            default_status_id=data.default_status_id,
            default_type_id=data.default_type_id,
            auto_ticket_missed_calls=data.auto_ticket_missed_calls,
            auto_ticket_voicemails=data.auto_ticket_voicemails,
            auto_ticket_completed_calls=data.auto_ticket_completed_calls,
            min_call_duration_seconds=data.min_call_duration_seconds,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def update_config(self, config_id: uuid.UUID, data: CWConfigUpdate) -> CWConfig:
        result = await self.db.execute(
            select(CWConfig).where(CWConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("ConnectWise config not found")

        update_data = data.model_dump(exclude_unset=True)

        # Encrypt keys if provided
        public_key = update_data.pop("public_key", None)
        if public_key:
            config.public_key_encrypted = encrypt_value(public_key)

        private_key = update_data.pop("private_key", None)
        if private_key:
            config.private_key_encrypted = encrypt_value(private_key)

        for key, value in update_data.items():
            setattr(config, key, value)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def delete_config(self, config_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(CWConfig).where(CWConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("ConnectWise config not found")
        await self.db.delete(config)
        await self.db.commit()

    # ── Client factory ─────────────────────────────────────────

    def _build_client(self, config: CWConfig) -> ConnectWiseClient:
        return ConnectWiseClient(
            company_id=config.company_id,
            public_key=decrypt_value(config.public_key_encrypted),
            private_key=decrypt_value(config.private_key_encrypted),
            client_id=config.client_id,
            base_url=config.base_url,
            redis=self.redis,
            tenant_id=str(config.tenant_id),
        )

    # ── Test connection ────────────────────────────────────────

    async def test_connection(self, config_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(CWConfig).where(CWConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("ConnectWise config not found")

        client = self._build_client(config)
        return await client.test_connection()

    # ── Company mappings ───────────────────────────────────────

    async def list_company_mappings(self, config_id: uuid.UUID) -> list[CWCompanyMapping]:
        result = await self.db.execute(
            select(CWCompanyMapping)
            .where(CWCompanyMapping.cw_config_id == config_id)
            .order_by(CWCompanyMapping.cw_company_name)
        )
        return list(result.scalars().all())

    async def add_company_mapping(
        self, config_id: uuid.UUID, data: CWCompanyMappingCreate
    ) -> CWCompanyMapping:
        if not data.extension_id and not data.did_id:
            raise ValueError("At least one of extension_id or did_id is required")

        mapping = CWCompanyMapping(
            cw_config_id=config_id,
            cw_company_id=data.cw_company_id,
            cw_company_name=data.cw_company_name,
            extension_id=data.extension_id,
            did_id=data.did_id,
        )
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping

    async def remove_company_mapping(self, mapping_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(CWCompanyMapping).where(CWCompanyMapping.id == mapping_id)
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            raise ValueError("Company mapping not found")
        await self.db.delete(mapping)
        await self.db.commit()

    # ── CW API proxies ─────────────────────────────────────────

    async def search_cw_companies(self, tenant_id: uuid.UUID, query: str) -> list[dict]:
        config = await self.get_config(tenant_id)
        if not config or not config.is_active:
            return []
        client = self._build_client(config)
        return await client.get_companies(query)

    async def get_cw_boards(self, tenant_id: uuid.UUID) -> list[dict]:
        config = await self.get_config(tenant_id)
        if not config or not config.is_active:
            return []
        client = self._build_client(config)
        return await client.get_boards()

    async def get_cw_board_statuses(self, tenant_id: uuid.UUID, board_id: int) -> list[dict]:
        config = await self.get_config(tenant_id)
        if not config or not config.is_active:
            return []
        client = self._build_client(config)
        return await client.get_ticket_statuses(board_id)

    async def get_cw_board_types(self, tenant_id: uuid.UUID, board_id: int) -> list[dict]:
        config = await self.get_config(tenant_id)
        if not config or not config.is_active:
            return []
        client = self._build_client(config)
        return await client.get_ticket_types(board_id)

    # ── Ticket creation from CDR ───────────────────────────────

    async def create_ticket_from_cdr(self, tenant_id: uuid.UUID, cdr_id: uuid.UUID) -> None:
        """Main entry point — called from ESL event listener after CDR commit."""
        config = await self.get_config(tenant_id)
        if not config or not config.is_active:
            return

        # Load CDR
        result = await self.db.execute(
            select(CallDetailRecord).where(CallDetailRecord.id == cdr_id)
        )
        cdr = result.scalar_one_or_none()
        if not cdr:
            logger.warning("cw_ticket_cdr_not_found", cdr_id=str(cdr_id))
            return

        # Determine trigger type
        trigger_type = self._determine_trigger(cdr)
        if not trigger_type:
            return

        # Check if trigger is enabled
        if not self._is_trigger_enabled(config, trigger_type):
            return

        # Check minimum duration for completed calls
        if trigger_type == "completed_call" and cdr.duration_seconds < config.min_call_duration_seconds:
            return

        # Look up CW company via mappings
        cw_company_id = await self._resolve_company(config.id, cdr)

        # Build ticket content
        summary, detail = self._build_ticket_content(cdr, trigger_type)

        # Create ticket via CW API
        client = self._build_client(config)
        ticket_log = CWTicketLog(
            cw_config_id=config.id,
            cdr_id=cdr.id,
            cw_company_id=cw_company_id,
            trigger_type=trigger_type,
            ticket_summary=summary,
        )

        try:
            result = await client.create_ticket(
                summary=summary,
                board_id=config.default_board_id,
                company_id=cw_company_id,
                status_id=config.default_status_id,
                type_id=config.default_type_id,
                initial_description=detail,
            )
            ticket_id = result.get("id", 0)
            ticket_log.cw_ticket_id = ticket_id
            ticket_log.status = "created"

            # Update CDR with ticket reference
            cdr.connectwise_ticket_id = ticket_id

            logger.info(
                "cw_ticket_created",
                ticket_id=ticket_id,
                trigger=trigger_type,
                tenant_id=str(tenant_id),
            )
        except Exception as e:
            ticket_log.cw_ticket_id = 0
            ticket_log.status = "failed"
            ticket_log.error_message = str(e)[:500]
            logger.error(
                "cw_ticket_creation_failed",
                error=str(e),
                trigger=trigger_type,
                tenant_id=str(tenant_id),
            )

        self.db.add(ticket_log)
        await self.db.commit()

    def _determine_trigger(self, cdr: CallDetailRecord) -> str | None:
        """Map CDR disposition to trigger type."""
        if cdr.disposition == "voicemail":
            return "voicemail"
        if cdr.disposition in ("no_answer", "busy", "cancelled"):
            return "missed_call"
        if cdr.disposition == "answered":
            return "completed_call"
        return None

    def _is_trigger_enabled(self, config: CWConfig, trigger_type: str) -> bool:
        if trigger_type == "missed_call":
            return config.auto_ticket_missed_calls
        if trigger_type == "voicemail":
            return config.auto_ticket_voicemails
        if trigger_type == "completed_call":
            return config.auto_ticket_completed_calls
        return False

    async def _resolve_company(self, config_id: uuid.UUID, cdr: CallDetailRecord) -> int | None:
        """Look up CW company from extension or DID mapping."""
        conditions = []
        if cdr.extension_id:
            conditions.append(CWCompanyMapping.extension_id == cdr.extension_id)
        if cdr.did_id:
            conditions.append(CWCompanyMapping.did_id == cdr.did_id)

        if not conditions:
            return None

        result = await self.db.execute(
            select(CWCompanyMapping.cw_company_id)
            .where(CWCompanyMapping.cw_config_id == config_id, or_(*conditions))
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _build_ticket_content(self, cdr: CallDetailRecord, trigger_type: str) -> tuple[str, str]:
        """Build ticket summary and detail text from CDR."""
        caller = cdr.caller_name or cdr.caller_number or "Unknown"
        number = cdr.caller_number or "Unknown"
        called = cdr.called_number or "Unknown"
        duration_str = (
            f"{cdr.duration_seconds // 60}m {cdr.duration_seconds % 60}s"
            if cdr.duration_seconds
            else "0s"
        )
        time_str = (
            cdr.start_time.strftime("%Y-%m-%d %H:%M:%S %Z") if cdr.start_time else "Unknown"
        )

        if trigger_type == "missed_call":
            summary = f"Missed call from {caller} ({number})"
            detail = (
                f"Missed Call Details:\n"
                f"- Caller: {caller} ({number})\n"
                f"- Called: {called}\n"
                f"- Time: {time_str}\n"
                f"- Ring Duration: {cdr.ring_seconds}s\n"
                f"- Direction: {cdr.direction}"
            )
        elif trigger_type == "voicemail":
            summary = f"Voicemail from {caller} ({number})"
            detail = (
                f"Voicemail Details:\n"
                f"- Caller: {caller} ({number})\n"
                f"- Called: {called}\n"
                f"- Time: {time_str}\n"
                f"- Duration: {duration_str}\n"
                f"- Direction: {cdr.direction}"
            )
        else:
            summary = f"Call from {caller} ({number}) — {duration_str}"
            detail = (
                f"Call Details:\n"
                f"- Caller: {caller} ({number})\n"
                f"- Called: {called}\n"
                f"- Time: {time_str}\n"
                f"- Duration: {duration_str}\n"
                f"- Direction: {cdr.direction}\n"
                f"- Disposition: {cdr.disposition}"
            )

        return summary, detail

    # ── Ticket logs ────────────────────────────────────────────

    async def get_ticket_logs(
        self,
        config_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CWTicketLog]:
        result = await self.db.execute(
            select(CWTicketLog)
            .where(CWTicketLog.cw_config_id == config_id)
            .order_by(CWTicketLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_ticket_log_stats(self, config_id: uuid.UUID) -> dict:
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        base_q = select(func.count()).where(CWTicketLog.cw_config_id == config_id)

        today_result = await self.db.execute(
            base_q.where(CWTicketLog.created_at >= today_start)
        )
        week_result = await self.db.execute(
            base_q.where(CWTicketLog.created_at >= week_start)
        )
        month_result = await self.db.execute(
            base_q.where(CWTicketLog.created_at >= month_start)
        )
        total_result = await self.db.execute(base_q)

        return {
            "today": today_result.scalar() or 0,
            "this_week": week_result.scalar() or 0,
            "this_month": month_result.scalar() or 0,
            "total": total_result.scalar() or 0,
        }
