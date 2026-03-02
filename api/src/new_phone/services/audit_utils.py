import uuid

import structlog
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.models.user import User
from new_phone.services.audit_service import AuditService

logger = structlog.get_logger()


async def log_audit(
    db: AsyncSession,
    user: User | None,
    request: Request,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,
    changes: dict | None = None,
) -> None:
    """Log an audit entry. Never raises — audit failures are logged but don't break requests."""
    try:
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")

        service = AuditService(db)
        await service.create_entry(
            user_id=user.id if user else None,
            tenant_id=user.tenant_id if user else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception as e:
        logger.warning(
            "audit_log_failed",
            error=str(e),
            action=action,
            resource_type=resource_type,
        )
