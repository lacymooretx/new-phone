import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.extension import Extension
from new_phone.models.security_config import SecurityConfig
from new_phone.models.silent_intercom import SessionStatus, SilentIntercomSession
from new_phone.schemas.silent_intercom import SilentIntercomStartRequest

logger = structlog.get_logger()


class SilentIntercomService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_session(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, data: SilentIntercomStartRequest
    ) -> SilentIntercomSession:
        await set_tenant_context(self.db, tenant_id)

        # Check tenant opt-in
        config_result = await self.db.execute(
            select(SecurityConfig).where(SecurityConfig.tenant_id == tenant_id)
        )
        config = config_result.scalar_one_or_none()
        if not config or not config.silent_intercom_enabled:
            raise ValueError("Silent intercom is not enabled for this tenant")

        # Load target extension
        target_ext_result = await self.db.execute(
            select(Extension).where(
                Extension.id == data.target_extension_id,
                Extension.tenant_id == tenant_id,
                Extension.is_active.is_(True),
            )
        )
        target_ext = target_ext_result.scalar_one_or_none()
        if not target_ext:
            raise ValueError("Target extension not found")

        # Create session record
        session_record = SilentIntercomSession(
            tenant_id=tenant_id,
            initiated_by_user_id=user_id,
            target_extension_id=data.target_extension_id,
            status=SessionStatus.ACTIVE,
            max_duration_seconds=config.silent_intercom_max_seconds,
        )
        self.db.add(session_record)
        await self.db.commit()
        await self.db.refresh(session_record)

        # Originate eavesdrop call via FreeSWITCH (best effort)
        try:
            from new_phone.main import freeswitch_service

            if freeswitch_service:
                # Find an active channel for the target extension
                channels = await freeswitch_service.show_channels_for_user(target_ext.sip_username)
                if channels:
                    target_uuid = channels[0]  # First active channel
                    # Find listener's extension
                    listener_ext_result = await self.db.execute(
                        select(Extension).where(
                            Extension.tenant_id == tenant_id,
                            Extension.user_id == user_id,
                            Extension.is_active.is_(True),
                        )
                    )
                    listener_ext = listener_ext_result.scalar_one_or_none()
                    if listener_ext:
                        fs_uuid = await freeswitch_service.originate_eavesdrop(
                            listener_ext.sip_username,
                            target_uuid,
                            config.silent_intercom_max_seconds,
                        )
                        if fs_uuid:
                            session_record.fs_uuid = fs_uuid
                            await self.db.commit()
                else:
                    logger.warning(
                        "silent_intercom_no_active_channel", target=target_ext.sip_username
                    )
        except Exception as e:
            logger.error("silent_intercom_originate_failed", error=str(e))

        logger.info(
            "silent_intercom_started",
            session_id=str(session_record.id),
            target=target_ext.sip_username,
            user_id=str(user_id),
        )

        return session_record

    async def end_session(
        self, tenant_id: uuid.UUID, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> SilentIntercomSession:
        await set_tenant_context(self.db, tenant_id)
        session_record = await self.get_session(tenant_id, session_id)
        if not session_record:
            raise ValueError("Silent intercom session not found")
        if session_record.status != SessionStatus.ACTIVE:
            raise ValueError(f"Session is not active (status: {session_record.status})")

        # Kill the FreeSWITCH channel
        if session_record.fs_uuid:
            try:
                from new_phone.main import freeswitch_service

                if freeswitch_service:
                    await freeswitch_service.uuid_kill(session_record.fs_uuid)
            except Exception as e:
                logger.error("silent_intercom_kill_failed", error=str(e))

        session_record.status = SessionStatus.ENDED_MANUAL
        session_record.ended_at = datetime.now(UTC)
        session_record.ended_by_user_id = user_id
        await self.db.commit()
        await self.db.refresh(session_record)

        logger.info("silent_intercom_ended", session_id=str(session_id), ended_by=str(user_id))
        return session_record

    async def list_sessions(
        self, tenant_id: uuid.UUID, limit: int = 50
    ) -> list[SilentIntercomSession]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SilentIntercomSession)
            .where(SilentIntercomSession.tenant_id == tenant_id)
            .order_by(SilentIntercomSession.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_session(
        self, tenant_id: uuid.UUID, session_id: uuid.UUID
    ) -> SilentIntercomSession | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SilentIntercomSession).where(
                SilentIntercomSession.id == session_id,
                SilentIntercomSession.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()
