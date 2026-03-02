"""Pytest configuration and fixtures for The Vault tests."""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from vault.main import app
from vault.storage import Base, get_db, get_db_session
from vault.storage.models import Project, Symbol, ProjectType, IndexStatus, SymbolType
from vault.storage.repositories import ProjectRepository, SymbolRepository


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def temp_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a temporary in-memory SQLite database for testing."""
    import sqlite3
    from uuid import UUID
    
    # Create in-memory database with UUID support
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            "detect_types": sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        },
    )
    
    # Register UUID adapters for the test database
    def adapt_uuid(uuid_obj):
        return str(uuid_obj)

    def convert_uuid(s):
        return UUID(s)

    sqlite3.register_adapter(UUID, adapt_uuid)
    sqlite3.register_converter("UUID", convert_uuid)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = AsyncSession(engine, expire_on_commit=False)
    
    yield async_session
    
    await async_session.close()
    await engine.dispose()


@pytest.fixture(autouse=True)
async def setup_api_dependencies(temp_db: AsyncSession):
    """Override API dependencies to use the test database."""
    async def override_get_db():
        yield temp_db
    
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def override_get_db_session():
        try:
            yield temp_db
            await temp_db.commit()
        except Exception:
            await temp_db.rollback()
            raise
        finally:
            pass  # Don't close the session, it's managed by the fixture
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_session] = override_get_db_session
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def project_repo(temp_db: AsyncSession) -> ProjectRepository:
    """Get a project repository instance."""
    return ProjectRepository(temp_db)


@pytest_asyncio.fixture
async def symbol_repo(temp_db: AsyncSession) -> SymbolRepository:
    """Get a symbol repository instance."""
    return SymbolRepository(temp_db)


@pytest.fixture
def temp_project_dir() -> Path:
    """Create a temporary directory for test projects."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_project() -> Project:
    """Create a sample project for testing."""
    return Project(
        id=uuid4(),
        name="TestProject",
        path="/test/project",
        type=ProjectType.PYTHON,
        language_primary="python",
        loc_total=100,
        file_count=5,
        health_score=0.8,
        index_status=IndexStatus.PENDING,
        git_has=False,
    )


@pytest.fixture
def sample_symbol() -> Symbol:
    """Create a sample symbol for testing."""
    return Symbol(
        id=uuid4(),
        project_id=uuid4(),
        file_path="test.py",
        symbol_type=SymbolType.FUNCTION,
        name="test_function",
        qualified_name="test_function",
        signature="def test_function():",
        line_start=1,
        line_end=5,
        raw_code="def test_function():\n    pass",
        content_hash="abc123",
        has_todo=False,
    )


@pytest.fixture
def csharp_sample_files() -> dict[str, str]:
    """Sample C# code files for testing."""
    return {
        "TestClass.cs": """
using System;

namespace TestProject
{
    public class TestClass
    {
        private readonly string _name;
        
        public TestClass(string name)
        {
            _name = name;
        }
        
        public string GetName()
        {
            return _name;
        }
        
        // TODO: Add validation
        public void SetName(string name)
        {
            _name = name;
        }
    }
}
""",
        "IInterface.cs": """
namespace TestProject
{
    public interface IInterface
    {
        string GetName();
        void SetName(string name);
    }
}
""",
        "Constants.cs": """
namespace TestProject
{
    public static class Constants
    {
        public const string DEFAULT_NAME = "Unknown";
        public const int MAX_LENGTH = 100;
    }
}
""",
    }


@pytest.fixture
def java_sample_files() -> dict[str, str]:
    """Sample Java code files for testing."""
    return {
        "TestClass.java": """
package com.example;

public class TestClass {
    private String name;
    
    public TestClass(String name) {
        this.name = name;
    }
    
    public String getName() {
        return name;
    }
    
    // TODO: Add validation
    public void setName(String name) {
        this.name = name;
    }
}
""",
        "Interface.java": """
package com.example;

public interface Interface {
    String getName();
    void setName(String name);
}
""",
        "Constants.java": """
package com.example;

public class Constants {
    public static final String DEFAULT_NAME = "Unknown";
    public static final int MAX_LENGTH = 100;
}
""",
    }


@pytest.fixture
def python_sample_files() -> dict[str, str]:
    """Sample Python code files for testing."""
    return {
        "test_class.py": """
class TestClass:
    def __init__(self, name: str):
        self.name = name
    
    def get_name(self) -> str:
        return self.name
    
    # TODO: Add validation
    def set_name(self, name: str) -> None:
        self.name = name

def test_function():
    pass

MAX_LENGTH = 100
""",
        "constants.py": """
DEFAULT_NAME = "Unknown"
VERSION = "1.0.0"
""",
    }


@pytest.fixture
def javascript_sample_files() -> dict[str, str]:
    """Sample JavaScript code files for testing."""
    return {
        "TestClass.js": """
class TestClass {
    constructor(name) {
        this.name = name;
    }
    
    getName() {
        return this.name;
    }
    
    // TODO: Add validation
    setName(name) {
        this.name = name;
    }
}

function testFunction() {
    return null;
}

const MAX_LENGTH = 100;
""",
        "constants.js": """
export const DEFAULT_NAME = "Unknown";
export const VERSION = "1.0.0";
""",
    }


@pytest.fixture
def renpy_sample_files() -> dict[str, str]:
    """Sample RenPy code files for testing."""
    return {
        "script.rpy": """
define e = Character("Eileen")

label start:
    "Hello World"
    
    # TODO: Add more dialogue
    jump ending

label ending:
    "The End"
    return
""",
        "characters.rpy": """
define narrator = Character("Narrator")
define player = Character("Player")

label character_intro:
    narrator "This is the character introduction."
    player "Hello, I'm the player character."
    return
""",
    }
