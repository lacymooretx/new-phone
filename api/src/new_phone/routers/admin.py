"""Admin endpoints for platform operations."""

from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Body, Depends
from sqlalchemy import select

from new_phone.auth.encryption import encrypt_value
from new_phone.auth.passwords import hash_password
from new_phone.db.engine import AdminSessionLocal
from new_phone.deps.auth import require_role
from new_phone.models.extension import Extension
from new_phone.models.voicemail_box import VoicemailBox
from new_phone.services.cdr_service import CDRService
from new_phone.services.voicemail_message_service import VoicemailMessageService

logger = structlog.get_logger()

router = APIRouter(tags=["admin"])


@router.post(
    "/admin/resync-credentials",
    dependencies=[Depends(require_role("msp_super_admin"))],
)
async def resync_credentials():
    """Regenerate encrypted SIP passwords and voicemail PINs for records with NULL values.

    This populates the encrypted_sip_password and encrypted_pin columns
    for any records created before Phase 3 that only have hashed values.
    Since bcrypt hashes are one-way, new random credentials are generated.
    """
    import secrets
    import string

    results = {"extensions_updated": 0, "voicemail_boxes_updated": 0}

    async with AdminSessionLocal() as session:
        # Find extensions with NULL encrypted_sip_password
        ext_result = await session.execute(
            select(Extension).where(Extension.encrypted_sip_password.is_(None))
        )
        extensions = list(ext_result.scalars().all())

        for ext in extensions:
            # Generate new SIP password (can't recover from bcrypt hash)
            new_password = "".join(
                secrets.choice(string.ascii_letters + string.digits) for _ in range(32)
            )
            ext.sip_password_hash = hash_password(new_password)
            ext.encrypted_sip_password = encrypt_value(new_password)
            results["extensions_updated"] += 1

        # Find voicemail boxes with NULL encrypted_pin
        vm_result = await session.execute(
            select(VoicemailBox).where(VoicemailBox.encrypted_pin.is_(None))
        )
        vm_boxes = list(vm_result.scalars().all())

        for box in vm_boxes:
            # Generate new 4-digit PIN
            new_pin = str(secrets.randbelow(9000) + 1000)
            box.pin_hash = hash_password(new_pin)
            box.encrypted_pin = encrypt_value(new_pin)
            results["voicemail_boxes_updated"] += 1

        await session.commit()

    logger.info("resync_credentials_complete", **results)
    return {
        "message": "Credentials resynced",
        "warning": "New random passwords/PINs were generated — phones must re-register",
        **results,
    }


@router.post(
    "/admin/cdr-cleanup",
    dependencies=[Depends(require_role("msp_super_admin"))],
)
async def cdr_cleanup(days: int = Body(90, ge=1, le=3650, embed=True)):
    """Purge CDRs older than N days. MSP admin only."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    async with AdminSessionLocal() as session:
        service = CDRService(session)
        deleted = await service.cleanup_old_cdrs(cutoff)
    logger.info("cdr_cleanup_complete", days=days, deleted=deleted)
    return {"message": f"Purged CDRs older than {days} days", "deleted": deleted}


@router.post(
    "/admin/voicemail-cleanup",
    dependencies=[Depends(require_role("msp_super_admin"))],
)
async def voicemail_cleanup(days: int = Body(30, ge=1, le=3650, embed=True)):
    """Purge deleted voicemail messages older than N days. MSP admin only."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    async with AdminSessionLocal() as session:
        service = VoicemailMessageService(session)
        deleted = await service.cleanup_old_messages(cutoff)
    logger.info("voicemail_cleanup_complete", days=days, deleted=deleted)
    return {"message": f"Purged deleted voicemail messages older than {days} days", "deleted": deleted}
