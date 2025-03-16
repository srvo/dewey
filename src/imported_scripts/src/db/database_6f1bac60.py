import os
from contextlib import asynccontextmanager

from models import Base
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Database configuration
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ethical_portfolio")

# Async database URL
ASYNC_DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Sync database URL (for migrations)
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# Create engines and session factory only when needed
def create_engines():
    # Create async engine
    async_engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=True,  # Set to False in production
        pool_size=20,
        max_overflow=10,
    )

    # Create sync engine for migrations
    sync_engine = create_engine(DATABASE_URL, echo=True)  # Set to False in production

    return async_engine, sync_engine


# Create async session factory
def create_session_factory(async_engine):
    return sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_db():
    """Async context manager for database sessions."""
    async_engine, _ = create_engines()
    AsyncSessionLocal = create_session_factory(async_engine)

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize the database."""
    async_engine, _ = create_engines()
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_db_sync() -> None:
    """Initialize the database synchronously (for migrations)."""
    _, sync_engine = create_engines()
    Base.metadata.create_all(sync_engine)


async def close_db() -> None:
    """Close database connections."""
    async_engine, sync_engine = create_engines()
    await async_engine.dispose()
    sync_engine.dispose()
