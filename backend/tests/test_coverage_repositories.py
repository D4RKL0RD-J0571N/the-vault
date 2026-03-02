"""Tests for vault.storage.repositories to improve coverage."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4
import sqlalchemy

from vault.storage.repositories import ProjectRepository, SymbolRepository
from vault.storage.models import Project, Symbol, ProjectType, IndexStatus, SymbolType
from vault.exceptions import DatabaseError, ProjectNotFoundError, SymbolNotFoundError

@pytest.mark.asyncio
async def test_project_repository_edges(temp_db):
    repo = ProjectRepository(temp_db)
    p_id = uuid4()
    
    # get_by_id not found
    assert await repo.get_by_id(p_id) is None
    
    # get_by_path not found
    assert await repo.get_by_path("/non/existent") is None
    
    # update not found
    with pytest.raises(ProjectNotFoundError):
        await repo.update(p_id, name="New")
        
    # create exception
    with patch.object(temp_db, "flush", side_effect=Exception("DB Error")):
        with pytest.raises(DatabaseError, match="Failed to create project"):
            await repo.create(Project(id=uuid4(), name="P", path="/p_err", type=ProjectType.PYTHON))

    # update exception
    p = Project(id=uuid4(), name="P", path="/p_ok", type=ProjectType.PYTHON)
    await repo.create(p)
    with patch.object(temp_db, "execute", side_effect=Exception("DB Error")):
        with pytest.raises(DatabaseError, match="Failed to update project"):
            # Update must use session.execute
            await repo.update(p.id, name="New")

    # delete exception
    with patch.object(temp_db, "execute", side_effect=Exception("DB Error")):
        with pytest.raises(DatabaseError, match="Failed to delete project"):
            await repo.delete(p.id)

@pytest.mark.asyncio
async def test_symbol_repository_edges(temp_db):
    repo = SymbolRepository(temp_db)
    s_id = uuid4()
    p_id = uuid4()
    
    # create batch exception
    with patch.object(temp_db, "flush", side_effect=Exception("DB Error")):
        with pytest.raises(DatabaseError, match="Failed to create symbols batch"):
            await repo.create_batch([Symbol(
                id=uuid4(), project_id=p_id, file_path="f.py", 
                symbol_type=SymbolType.FUNCTION, name="n", qualified_name="n", 
                line_start=1, line_end=2, content_hash="h"
            )])

    # delete_by_project exception
    with patch.object(temp_db, "execute", side_effect=Exception("DB Error")):
        with pytest.raises(DatabaseError, match="Failed to delete symbols"):
            await repo.delete_by_project(p_id)

    # delete_by_file exception
    with patch.object(temp_db, "execute", side_effect=Exception("DB Error")):
        with pytest.raises(DatabaseError, match="Failed to delete file symbols"):
            await repo.delete_by_file(p_id, "f.py")

    # update_todo_status exception
    with patch.object(temp_db, "execute", side_effect=Exception("DB Error")):
        with pytest.raises(DatabaseError, match="Failed to update symbol TODO status"):
            await repo.update_todo_status(s_id, True)

@pytest.mark.asyncio
async def test_project_repository_getters(temp_db):
    repo = ProjectRepository(temp_db)
    p = Project(id=uuid4(), name="P", path="/p_get", type=ProjectType.PYTHON, index_status=IndexStatus.PENDING)
    await repo.create(p)
    
    assert len(await repo.get_by_type(ProjectType.PYTHON)) == 1
    assert len(await repo.get_by_status(IndexStatus.PENDING)) == 1
    
    # update_status
    p2 = await repo.update_status(p.id, IndexStatus.COMPLETE)
    assert p2.index_status == IndexStatus.COMPLETE
