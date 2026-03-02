"""Database connection and session management for The Vault application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.pool import StaticPool

from vault.config import settings
from vault.storage.models import Base

# Create async engine
engine = create_async_engine(
    settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///"),
    echo=settings.environment == "development",
    poolclass=StaticPool,
    connect_args=(
        {"check_same_thread": False} if "sqlite" in settings.database_url else {}
    ),
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """Drop all database tables (for testing)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session with automatic cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session."""
    async with get_db_session() as session:
        yield session
