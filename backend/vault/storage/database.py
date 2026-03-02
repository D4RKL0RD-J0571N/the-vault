"""Database connection and session management for The Vault application."""

import sqlite3
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.pool import StaticPool

from vault.config import settings
from vault.storage.models import Base


# Custom UUID type handler for SQLite
def adapt_uuid(uuid_obj):
    """Convert UUID to string for SQLite."""
    return str(uuid_obj)


def convert_uuid(s):
    """Convert string back to UUID from SQLite."""
    return UUID(s)


# Register the adapters
sqlite3.register_adapter(UUID, adapt_uuid)
sqlite3.register_converter("UUID", convert_uuid)


# Create async engine
engine = create_async_engine(
    settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///"),
    echo=settings.environment == "development",
    poolclass=StaticPool,
    connect_args=(
        {
            "check_same_thread": False,
            "detect_types": sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        }
        if "sqlite" in settings.database_url
        else {}
    ),
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas and register UUID type."""
    if "sqlite" in settings.database_url:
        dbapi_connection.text_factory = str
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


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
