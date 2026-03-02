"""Tests for vault.storage.database and final gap closure."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from vault.storage.database import init_db, drop_db, get_db_session, get_db
from vault.storage.models import Base
from vault.config import settings

@pytest.mark.asyncio
async def test_database_init_drop():
    # Hit init_db and drop_db
    # Patch the engine object itself in the module
    with patch("vault.storage.database.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        
        await init_db()
        mock_conn.run_sync.assert_called_with(Base.metadata.create_all)
        
        await drop_db()
        mock_conn.run_sync.assert_called_with(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_get_db_session_rollback():
    # Hit rollback branch in get_db_session
    # We need to mock AsyncSessionLocal so it returns a mock session
    # and ensures that error during yield triggers rollback.
    mock_session = AsyncMock()
    # Mock the return value of AsyncSessionLocal() context manager
    with patch("vault.storage.database.AsyncSessionLocal") as mock_factory:
        mock_factory.return_value.__aenter__.return_value = mock_session
        
        try:
            async with get_db_session() as session:
                raise Exception("Trigger rollback")
        except Exception:
            pass
            
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

@pytest.mark.asyncio
async def test_get_db_yield():
    # Hit get_db branches
    with patch("vault.storage.database.get_db_session") as mock_get_session:
        mock_session = MagicMock()
        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session
            
        mock_get_session.return_value = mock_session_ctx()
        
        async for session in get_db():
            assert session == mock_session

@pytest.mark.asyncio
async def test_config_validators():
    from vault.config import Settings
    s = Settings()
    
    # Hit validators
    with pytest.raises(ValueError, match="Environment must be one of"):
        Settings(environment="invalid")
        
    with pytest.raises(ValueError, match="Log level must be one of"):
        Settings(log_level="TRACE")
        
    # parse_root_directories validator
    s2 = Settings(root_directories="a,b,c")
    assert s2.root_directories == ["a", "b", "c"]
