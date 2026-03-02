"""Tests for the ParsingService and background parsing management."""

import pytest
from uuid import uuid4
from vault.parser import ParsingService
from vault.storage.models import Project, ProjectType, IndexStatus

class TestParsingService:
    """Test cases for ParsingService logic."""

    @pytest.mark.asyncio
    async def test_start_parsing_project_and_wait(self, project_repo, symbol_repo, tmp_path):
        """Test starting a parsing task and waiting for completion."""
        service = ParsingService(project_repo, symbol_repo)
        
        # Setup real file
        project_dir = tmp_path / "parse_test"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("def hello(): pass")
        
        project = Project(
            id=uuid4(),
            name="ParseTest",
            path=str(project_dir),
            type=ProjectType.PYTHON
        )
        await project_repo.create(project)
        
        result = await service.start_parsing_project(project.id)
        assert result["success"] is True
        
        # Wait for background task
        task = service._active_tasks.get(project.id)
        if task:
            await task
            
        # Verify status updated
        project_after = await project_repo.get_by_id(project.id)
        assert project_after.index_status == IndexStatus.COMPLETE
        
        # Verify symbols
        symbols = await symbol_repo.get_by_project(project.id)
        assert len(symbols) == 1

    @pytest.mark.asyncio
    async def test_get_parsing_status_not_found(self, project_repo, symbol_repo):
        """Test retrieving status for a non-existent project."""
        service = ParsingService(project_repo, symbol_repo)
        status = await service.get_parsing_status(uuid4())
        assert status["success"] is False
        assert "not found" in status["error"]

    @pytest.mark.asyncio
    async def test_batch_parse_empty_list(self, project_repo, symbol_repo):
        """Test batch parsing with an empty list."""
        service = ParsingService(project_repo, symbol_repo)
        result = await service.parse_multiple_projects([])
        assert result["success"] is True
        assert result["projects_attempted"] == 0

    @pytest.mark.asyncio
    async def test_reparse_changed_file_logic(self, project_repo, symbol_repo, tmp_path):
        """Test the logic for reparsing a single changed file."""
        service = ParsingService(project_repo, symbol_repo)
        
        # Setup real file
        project_dir = tmp_path / "my_project"
        project_dir.mkdir()
        file_path = project_dir / "app.py"
        file_path.write_text("def main(): pass")
        
        project = Project(
            id=uuid4(),
            name="MyProject",
            path=str(project_dir),
            type=ProjectType.PYTHON
        )
        await project_repo.create(project)
        
        # Reparse
        result = await service.parser.reparse_changed_file(project.id, "app.py")
        assert result.get("success") is True, f"Reparse failed: {result.get('error')}"
        assert result["symbols_extracted"] == 1
        
        # Verify symbol exists
        symbols = await symbol_repo.get_by_project(project.id)
        assert len(symbols) == 1
        assert symbols[0].name == "main"

    @pytest.mark.asyncio
    async def test_parse_project_not_found_error(self, project_repo, symbol_repo):
        """Test parse_project handles missing project gracefully."""
        service = ParsingService(project_repo, symbol_repo)
        result = await service.start_parsing_project(uuid4())
        # The service returns success:False in the response dict instead of raising
        assert result["success"] is False
        assert "not found" in result["message"]
