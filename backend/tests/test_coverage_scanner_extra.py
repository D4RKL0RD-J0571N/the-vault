"""Extra tests for scanner.py to hit missing branches."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from vault.crawler import ProjectScanner
from vault.storage.models import ProjectType, IndexStatus

@pytest.mark.asyncio
async def test_scanner_extra_branches():
    repo = MagicMock()
    scanner = ProjectScanner(repo)
    
    # 1. scan_root_directories: no root paths (Line 24-27)
    with patch("vault.config.settings.root_directories", []):
        with pytest.raises(ValueError, match="No root directories"):
            await scanner.scan_root_directories()
            
    # 2. _scan_directory branches (Lines 73, 77, 86-87)
    # We need a directory with: 
    # - a file (hits 73)
    # - an excluded dir (hits 77)
    # - a nested dir that is not a project (hits 86-87)
    with patch("pathlib.Path.iterdir") as mock_iter:
        f = MagicMock()
        f.is_dir.return_value = False
        
        excluded_dir = MagicMock()
        excluded_dir.is_dir.return_value = True
        excluded_dir.name = ".git"
        
        nested_dir = MagicMock()
        nested_dir.is_dir.return_value = True
        nested_dir.name = "normal_dir"
        nested_dir.iterdir.return_value = [] # End recursion
        
        mock_iter.return_value = [f, excluded_dir, nested_dir]
        
        with patch.object(scanner, "_is_project_directory", AsyncMock(return_value=False)):
            res = await scanner._scan_directory(Path("/test"))
            assert res == []

    # 3. _is_project_directory: OTHER type with files (Line 101-102)
    with patch.object(scanner.fingerprinter, "detect_project_type", return_value=ProjectType.OTHER):
        with patch.object(scanner.fingerprinter, "calculate_metrics", return_value=(5, 100, [])):
            assert await scanner._is_project_directory(Path("/test")) is True

    # 4. _create_or_update_project: existing project (Line 115-119)
    repo.get_by_path = AsyncMock(return_value=MagicMock(id="p1"))
    metadata = {"name": "P1", "type": ProjectType.PYTHON, "file_count": 1, "loc_total": 1, "languages": {}}
    with patch.object(scanner.fingerprinter, "get_project_metadata", return_value=metadata):
        repo.update = AsyncMock(return_value=MagicMock())
        res = await scanner._create_or_update_project(Path("/test"))
        assert res is not None
        repo.update.assert_called_once()
