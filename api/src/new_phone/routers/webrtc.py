import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import decrypt_value
from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.config import settings
from new_phone.deps.auth import get_admin_db, get_current_user, require_permission
from new_phone.models.extension import Extension
from new_phone.models.user import User
from new_phone.schemas.webrtc import WebRTCCredentials

logger = structlog.get_logger()

router = APIRouter(tags=["webrtc"])


def _build_credentials(ext: Extension) -> WebRTCCredentials:
    """Build WebRTC credentials response from an extension."""
    if not ext.encrypted_sip_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SIP password not available — re-generate via password reset",
        )

    sip_password = decrypt_value(ext.encrypted_sip_password)

    # WSS URL: use explicit config if set, otherwise /wss (browser resolves relative to page origin)
    if settings.freeswitch_wss_url:
        wss_url = settings.freeswitch_wss_url
    else:
        wss_url = "/wss"

    # SIP domain: use the FreeSWITCH internal hostname for SIP REGISTER
    sip_domain = settings.freeswitch_host

    display_name = ext.internal_cid_name or f"Ext {ext.extension_number}"

    return WebRTCCredentials(
        sip_username=ext.sip_username,
        sip_password=sip_password,
        sip_domain=sip_domain,
        wss_url=wss_url,
        extension_number=ext.extension_number,
        extension_id=ext.id,
        display_name=display_name,
    )


@router.get(
    "/tenants/{tenant_id}/extensions/{ext_id}/webrtc-credentials",
    response_model=WebRTCCredentials,
)
async def get_webrtc_credentials(
    tenant_id: uuid.UUID,
    ext_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Get WebRTC/SIP.js credentials for a specific extension.

    MSP/tenant_admin can access any extension in their scope.
    Tenant managers and users can only access their own extension.
    """
    # Tenant access check
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    result = await db.execute(
        select(Extension).where(
            Extension.id == ext_id,
            Extension.tenant_id == tenant_id,
            Extension.is_active.is_(True),
        )
    )
    ext = result.scalar_one_or_none()
    if not ext:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extension not found")

    # Non-admin users can only get credentials for their own extension
    if not is_msp_role(user.role) and user.role not in ("tenant_admin",) and ext.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return _build_credentials(ext)


@router.get("/me/webrtc-credentials", response_model=WebRTCCredentials)
async def get_my_webrtc_credentials(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Get WebRTC credentials for the current user's assigned extension."""
    result = await db.execute(
        select(Extension).where(
            Extension.user_id == user.id,
            Extension.is_active.is_(True),
        )
    )
    ext = result.scalar_one_or_none()
    if not ext:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No extension assigned to your account",
        )

    return _build_credentials(ext)
