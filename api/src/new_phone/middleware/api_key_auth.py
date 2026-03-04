"""X-API-Key authentication middleware alongside JWT."""


from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.deps.auth import get_admin_db
from new_phone.models.api_key import ApiKey
from new_phone.services.api_key_service import ApiKeyService


async def get_api_key_user(
    request: Request,
    db: AsyncSession = Depends(get_admin_db),
) -> ApiKey | None:
    """Extract and validate X-API-Key header. Returns None if no key provided."""
    api_key_header = request.headers.get("X-API-Key")
    if not api_key_header:
        return None

    service = ApiKeyService(db)
    key = await service.validate_key(api_key_header)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
        )
    return key


async def get_db_with_api_key_tenant(
    api_key: ApiKey,
    db: AsyncSession = Depends(get_admin_db),
) -> AsyncSession:
    """Set RLS tenant context based on the API key's tenant."""
    await set_tenant_context(db, api_key.tenant_id)
    return db
