import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.jwt import decode_token
from new_phone.auth.rbac import Permission, has_permission, is_msp_role
from new_phone.db.engine import AdminSessionLocal, AppSessionLocal
from new_phone.db.rls import set_tenant_context
from new_phone.models.user import User

security = HTTPBearer()


async def get_db() -> AsyncSession:
    """Yield a database session (no tenant context yet)."""
    async with AppSessionLocal() as session:
        yield session


async def get_admin_db() -> AsyncSession:
    """Yield an admin session that bypasses RLS.

    Used for auth (login/refresh) where tenant context is unknown.
    """
    async with AdminSessionLocal() as session:
        yield session


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
) -> User:
    """Decode JWT, load user from DB, validate active status."""
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from None

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )

    return user


async def get_db_with_tenant(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncSession:
    """Set RLS tenant context based on the current user, then yield the session."""
    await set_tenant_context(db, user.tenant_id)
    return db


def require_role(*roles: str):
    """FastAPI dependency that checks the user has one of the specified roles."""

    async def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not authorized",
            )
        return user

    return checker


def require_permission(permission: Permission):
    """FastAPI dependency that checks the user has a specific permission."""

    async def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return user

    return checker


def require_tenant_access(tenant_id_param: str = "tenant_id"):
    """Ensure user can access the specified tenant.

    MSP roles can access any tenant.
    Tenant-scoped roles can only access their own tenant.
    """

    async def checker(
        user: Annotated[User, Depends(get_current_user)],
        **kwargs,
    ) -> User:
        # MSP roles can access any tenant
        if is_msp_role(user.role):
            return user

        # Tenant roles must match
        target_tenant_id = kwargs.get(tenant_id_param)
        if target_tenant_id and uuid.UUID(str(target_tenant_id)) != user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access other tenant's resources",
            )
        return user

    return checker
