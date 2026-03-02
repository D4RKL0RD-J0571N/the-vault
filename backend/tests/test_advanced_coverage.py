"""Advanced tests for remaining coverage gaps with sophisticated mocking."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from fastapi import HTTPException
import asyncio

from vault.main import app
from vault.crawler.watcher import VaultFileEventHandler


class TestAdvancedAPICoverage:
    """Advanced tests for API dependency injection scenarios."""
    
    @pytest.mark.asyncio
    async def test_list_projects_repository_exception(self, temp_db):
        """Test generic exception handling in list_projects using dependency injection override."""
        from fastapi import FastAPI
        from vault.api.projects import get_project_repository
        from vault.storage.repositories import ProjectRepository
        
        # Create a mock repository that raises an exception
        mock_repo = Mock(spec=ProjectRepository)
        mock_repo.get_all.side_effect = RuntimeError("Database connection failed")
        
        # Override the dependency
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/projects/")
                
                assert response.status_code == 500
                assert "Failed to list projects: Database connection failed" in response.json()["detail"]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()
    
    # Skipping other API tests for now - complex dependency injection scenarios


class TestAdvancedExtractorCoverage:
    """Advanced tests for complex AST traversal scenarios."""
    
    @pytest.mark.asyncio
    async def test_extractor_comment_traversal_with_siblings(self):
        """Test extractor comment traversal with complex sibling chains (line 98)."""
        from vault.parser.extractors import PythonExtractor
        
        extractor = PythonExtractor()
        
        # Create a chain of comment siblings
        comment3 = Mock()
        comment3.type = "comment"
        comment3.prev_sibling = None
        comment3.start_byte = 0
        comment3.end_byte = 10
        
        comment2 = Mock()
        comment2.type = "comment"
        comment2.prev_sibling = comment3
        comment2.start_byte = 11
        comment2.end_byte = 20
        
        comment1 = Mock()
        comment1.type = "comment"
        comment1.prev_sibling = comment2
        comment1.start_byte = 21
        comment1.end_byte = 30
        
        node = Mock()
        node.prev_sibling = comment1
        node.type = "function"
        node.start_byte = 31
        node.end_byte = 40
        
        # Mock _get_node_text to return different content for each comment
        def mock_get_text(node, source_code):
            if node == comment1:
                return "# TODO: first comment"
            elif node == comment2:
                return "# Regular comment"
            elif node == comment3:
                return "# FIXME: third comment"
            return "def test(): pass"
        
        with patch.object(extractor, '_get_node_text', side_effect=mock_get_text):
            result = extractor._has_todo_near_node(node, "def test(): pass")
            # Should find TODO in first comment and return True
            assert result is True
    
    @pytest.mark.asyncio
    async def test_extractor_comment_traversal_no_todo(self):
        """Test extractor comment traversal when no TODO found (hits line 98)."""
        from vault.parser.extractors import PythonExtractor
        
        extractor = PythonExtractor()
        
        # Create a node with a comment sibling that has no TODO
        comment = Mock()
        comment.type = "comment"
        comment.prev_sibling = None  # This will hit line 98 when prev becomes None
        comment.start_byte = 0
        comment.end_byte = 10
        
        node = Mock()
        node.prev_sibling = comment
        node.type = "function"
        node.start_byte = 11
        node.end_byte = 20
        
        with patch.object(extractor, '_get_node_text', return_value="# Regular comment"):
            result = extractor._has_todo_near_node(node, "def test(): pass")
            assert result is False
    
    # Skipping complex AST error handling for now


class TestAdvancedFingerprintCoverage:
    """Advanced tests for fingerprinter edge cases."""
    
    @pytest.mark.asyncio
    async def test_fingerprint_modification_time_permission_error(self):
        """Test fingerprinter handling permission errors in modification time check."""
        from vault.crawler.fingerprint import ProjectFingerprinter
        from pathlib import Path
        
        fingerprinter = ProjectFingerprinter()
        
        # Mock os.walk and Path to simulate permission error
        with patch('vault.crawler.fingerprint.os.walk') as mock_walk:
            mock_walk.return_value = [("/test", [], ["file.py"])]
            
            with patch('vault.crawler.fingerprint.Path') as mock_path_class:
                # Create a mock Path that raises PermissionError on stat()
                mock_path = Mock(spec=Path)
                mock_file = Mock()
                mock_file.stat.side_effect = PermissionError("Access denied")
                
                # Fix the Path division
                mock_path.__truediv__ = Mock(return_value=mock_file)
                mock_path_class.return_value = mock_path
                
                with patch.object(fingerprinter, '_should_exclude_file', return_value=False):
                    # This should hit the error handling at lines 218->221, 221->209
                    timestamps = fingerprinter._get_directory_timestamps("/test")
                    assert timestamps["oldest"] is None
                    assert timestamps["newest"] is None
    
    @pytest.mark.asyncio
    async def test_fingerprint_modification_time_os_error(self):
        """Test fingerprinter handling various OS errors."""
        from vault.crawler.fingerprint import ProjectFingerprinter
        
        fingerprinter = ProjectFingerprinter()
        
        with patch('vault.crawler.fingerprint.os.walk') as mock_walk:
            mock_walk.return_value = [("/test", [], ["file.py"])]
            
            with patch('vault.crawler.fingerprint.Path') as mock_path_class:
                mock_path = Mock()
                mock_file = Mock()
                mock_file.stat.side_effect = OSError("File not found")
                
                mock_path.__truediv__ = Mock(return_value=mock_file)
                mock_path_class.return_value = mock_path
                
                with patch.object(fingerprinter, '_should_exclude_file', return_value=False):
                    timestamps = fingerprinter._get_directory_timestamps("/test")
                    assert timestamps["oldest"] is None
                    assert timestamps["newest"] is None


class TestAdvancedTreeSitterCoverage:
    """Advanced tests for tree-sitter parser edge cases."""
    
    @pytest.mark.asyncio
    async def test_parser_file_not_found_error(self, temp_db):
        """Test parser handling file not found errors."""
        from vault.parser.tree_sitter_parser import TreeSitterParser
        from vault.storage.repositories import ProjectRepository, SymbolRepository
        
        project_repo = ProjectRepository(temp_db)
        symbol_repo = SymbolRepository(temp_db)
        parser = TreeSitterParser(project_repo, symbol_repo)
        project_id = uuid4()
        
        # Mock project exists but file parsing fails
        with patch.object(parser.project_repo, 'get_by_id') as mock_get_project:
            mock_project = Mock()
            mock_project.path = "/test/project"
            mock_get_project.return_value = mock_project
            
            with patch.object(parser, '_parse_file', side_effect=FileNotFoundError("File not found")):
                with pytest.raises(FileNotFoundError):
                    await parser.parse_file(project_id, "nonexistent.py")
    
    @pytest.mark.asyncio
    async def test_parser_permission_error(self, temp_db):
        """Test parser handling permission errors during parsing."""
        from vault.parser.tree_sitter_parser import TreeSitterParser
        from vault.storage.repositories import ProjectRepository, SymbolRepository
        
        project_repo = ProjectRepository(temp_db)
        symbol_repo = SymbolRepository(temp_db)
        parser = TreeSitterParser(project_repo, symbol_repo)
        project_id = uuid4()
        
        with patch.object(parser.project_repo, 'get_by_id') as mock_get_project:
            mock_project = Mock()
            mock_project.path = "/test/project"
            mock_get_project.return_value = mock_project
            
            with patch.object(parser, '_parse_file', side_effect=PermissionError("Access denied")):
                with pytest.raises(PermissionError):
                    await parser.parse_file(project_id, "restricted.py")
    
    @pytest.mark.asyncio
    async def test_reparse_changed_file_with_symbols(self, temp_db):
        """Test reparse when symbols are found and need to be inserted."""
        from vault.parser.tree_sitter_parser import TreeSitterParser
        from vault.storage.repositories import ProjectRepository, SymbolRepository
        from vault.storage.models import Symbol
        
        project_repo = ProjectRepository(temp_db)
        symbol_repo = SymbolRepository(temp_db)
        parser = TreeSitterParser(project_repo, symbol_repo)
        project_id = uuid4()
        
        # Create mock symbols
        mock_symbol = Mock(spec=Symbol)
        
        with patch.object(parser.project_repo, 'get_by_id') as mock_get_project:
            mock_project = Mock()
            mock_project.path = "/test/project"
            mock_get_project.return_value = mock_project
            
            with patch.object(parser, '_parse_file', return_value=[mock_symbol]):
                with patch.object(parser.symbol_repo, 'create_batch') as mock_create:
                    result = await parser.reparse_changed_file(project_id, "test.py")
                    
                    assert result["success"] is True
                    assert result["symbols_extracted"] == 1
                    mock_create.assert_called_once_with([mock_symbol])


class TestAdvancedWatcherCoverage:
    """Advanced tests for file system watcher edge cases."""
    
    # Skipping complex watcher tests for now - debounce timing is tricky to test reliably
