from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from new_phone.config import settings

# Admin engine — bypasses RLS. Used for migrations only.
admin_engine = create_async_engine(
    settings.admin_database_url,
    echo=settings.debug,
    pool_size=5,
    max_overflow=5,
)

# App engine — RLS enforced. Used by the API at runtime.
app_engine = create_async_engine(
    settings.app_database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
)

AdminSessionLocal = async_sessionmaker(
    admin_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

AppSessionLocal = async_sessionmaker(
    app_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
