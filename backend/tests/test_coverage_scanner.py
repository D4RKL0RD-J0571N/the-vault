"""Tests for vault.crawler.scanner to improve coverage."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
from uuid import uuid4

from vault.crawler.scanner import ProjectScanner, ProjectDiscoveryService
from vault.storage.repositories import ProjectRepository
from vault.storage.models import Project, ProjectType, IndexStatus

@pytest.mark.asyncio
async def test_scanner_basic_branches(temp_db):
    repo = ProjectRepository(temp_db)
    scanner = ProjectScanner(repo)
    
    # scan_root_directories with empty list should raise if settings is empty too
    with patch("vault.crawler.scanner.settings") as mock_settings:
        mock_settings.root_directories = []
        with pytest.raises(ValueError, match="No root directories configured"):
            await scanner.scan_root_directories([])
        
        # Non-existent path
        mock_settings.root_directories = ["/non/existent/path"]
        projects = await scanner.scan_root_directories()
        assert len(projects) == 0

    # scan_directory non-existent
    with pytest.raises(ValueError, match="Directory does not exist"):
        await scanner.scan_directory("/invalid")

@pytest.mark.asyncio
async def test_refresh_project(temp_db):
    repo = MagicMock(spec=ProjectRepository)
    scanner = ProjectScanner(repo)
    
    # Not found
    repo.get_by_id = AsyncMock(return_value=None)
    assert await scanner.refresh_project(uuid4()) is None
    
    # Success
    p = Project(id=uuid4(), name="P", path="/p", type=ProjectType.PYTHON)
    repo.get_by_id = AsyncMock(return_value=p)
    repo.update = AsyncMock(return_value=p)
    
    with patch("vault.crawler.scanner.ProjectFingerprinter.get_project_metadata", return_value={}):
        res = await scanner.refresh_project(p.id)
        assert res == p

@pytest.mark.asyncio
async def test_scanner_exclude():
    scanner = ProjectScanner(MagicMock())
    
    # Hideen
    assert scanner._should_exclude_directory(Path(".git")) is True
    
    # Pattern
    with patch("vault.crawler.scanner.settings") as mock_settings:
        mock_settings.exclude_patterns = ["node_modules"]
        assert scanner._should_exclude_directory(Path("node_modules")) is True

@pytest.mark.asyncio
async def test_create_or_update_exception(temp_db):
    repo = MagicMock(spec=ProjectRepository)
    scanner = ProjectScanner(repo)
    
    repo.get_by_path = AsyncMock(side_effect=Exception("DB Error"))
    # Should hit lines 133-136
    res = await scanner._create_or_update_project(Path("/any"))
    assert res is None

@pytest.mark.asyncio
async def test_discovery_service_stats(temp_db):
    repo = ProjectRepository(temp_db)
    service = ProjectDiscoveryService(repo)
    
    # Add a project
    p = Project(
        id=uuid4(), name="P", path="/p", 
        type=ProjectType.PYTHON, 
        index_status=IndexStatus.COMPLETE,
        file_count=10, loc_total=100
    )
    await repo.create(p)
    
    stats = await service.get_project_statistics()
    assert stats["total_projects"] == 1
    assert stats["total_files"] == 10
    assert stats["total_loc"] == 100
    assert stats["by_type"]["python"] == 1
    assert stats["by_status"]["complete"] == 1

@pytest.mark.asyncio
async def test_scan_specific_path_error():
    service = ProjectDiscoveryService(MagicMock())
    res = await service.scan_specific_path("/invalid")
    assert res["success"] is False
    assert "Directory does not exist" in res["error"]
