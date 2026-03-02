import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_tenant_context(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Set the tenant context for RLS enforcement.

    Uses SET LOCAL so the setting is scoped to the current transaction
    and automatically cleared when the transaction ends — no pool leak.
    """
    await session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
