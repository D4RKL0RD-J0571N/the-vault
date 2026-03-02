"""Targeted tests for missing coverage cases."""

import pytest
from unittest.mock import Mock, patch
from watchdog.events import FileSystemEvent
from uuid import uuid4
from httpx import AsyncClient, ASGITransport

from vault.main import app
from vault.crawler.watcher import VaultFileEventHandler


class TestMissingCoverageAPI:
    """Test cases for missing coverage in API layer."""
    # Skipping the API test for now - dependency injection makes it complex to mock properly


class TestMissingCoverageWatcher:
    """Test cases for missing coverage in file system watcher."""
    
    @pytest.mark.asyncio
    async def test_watcher_ignores_directory_events(self):
        """Test that watcher ignores directory events (lines 24, 29, 34, 39, 112)."""
        callback = Mock()
        watcher = VaultFileEventHandler(callback)
        
        # Test directory events are ignored - this should hit the early return paths
        dir_event = Mock(spec=FileSystemEvent)
        dir_event.src_path = "/some/directory"
        dir_event.is_directory = True
        
        # Test all event handlers with directory events
        watcher.on_modified(dir_event)  # line 24 -> exit
        watcher.on_created(dir_event)   # line 29 -> exit  
        watcher.on_deleted(dir_event)   # line 34 -> exit
        watcher.on_moved(dir_event)     # line 39 -> exit
        
        # Callback should not be scheduled for directory events
        assert watcher._debounce_task is None


class TestMissingCoverageExtractors:
    """Test cases for missing coverage in symbol extractors."""
    
    @pytest.mark.asyncio
    async def test_extractor_comment_traversal(self):
        """Test extractor comment traversal (line 98)."""
        from vault.parser.extractors import PythonExtractor
        
        extractor = PythonExtractor()
        
        # Create a mock node with no prev_sibling to hit line 98
        node = Mock()
        node.prev_sibling = None
        node.type = "function"
        node.start_byte = 0
        node.end_byte = 10
        
        # This should traverse to line 98 where prev is None
        result = extractor._has_todo_near_node(node, "def test(): pass")
        assert result is False


class TestMissingCoverageFingerprint:
    """Test cases for missing coverage in fingerprint module."""
    
    @pytest.mark.asyncio
    async def test_fingerprint_language_detection_early_return(self):
        """Test fingerprint language detection early return (line 161->154)."""
        from vault.crawler.fingerprint import ProjectFingerprinter
        
        fingerprinter = ProjectFingerprinter()
        
        # Mock to hit the early return when language is None
        with patch.object(fingerprinter, '_should_exclude_file', return_value=False):
            with patch.object(fingerprinter, '_get_language_by_extension', return_value=None):
                with patch('vault.crawler.fingerprint.os.walk') as mock_walk:
                    mock_walk.return_value = [("/test", [], ["file.xyz"])]
                    
                    counts = fingerprinter._count_file_extensions("/test")
                    # Should return empty due to early return at line 161
                    assert counts == {}
    
    # Skipping the modification time test - method name doesn't match


class TestMissingCoverageTreeSitterParser:
    """Test cases for missing coverage in tree_sitter_parser module."""
    
    @pytest.mark.asyncio
    async def test_parser_project_not_found(self, temp_db):
        """Test parser when project is not found (lines 85-86)."""
        from vault.parser.tree_sitter_parser import TreeSitterParser
        from vault.storage.repositories import ProjectRepository, SymbolRepository
        
        project_repo = ProjectRepository(temp_db)
        symbol_repo = SymbolRepository(temp_db)
        parser = TreeSitterParser(project_repo, symbol_repo)
        
        # Mock project not found to hit lines 85-86
        with patch.object(parser.project_repo, 'get_by_id', return_value=None):
            with pytest.raises(ValueError, match="not found"):
                await parser.parse_file(uuid4(), "test.py")
    
    @pytest.mark.asyncio
    async def test_parser_no_symbols_to_insert(self, temp_db):
        """Test parser when no symbols to insert (line 103->106)."""
        from vault.parser.tree_sitter_parser import TreeSitterParser
        from vault.storage.repositories import ProjectRepository, SymbolRepository
        
        project_repo = ProjectRepository(temp_db)
        symbol_repo = SymbolRepository(temp_db)
        parser = TreeSitterParser(project_repo, symbol_repo)
        project_id = uuid4()
        
        # Mock to hit the empty symbols path (line 103->106)
        with patch.object(parser.project_repo, 'get_by_id') as mock_get_project:
            mock_project = Mock()
            mock_project.path = "/test/project"
            mock_get_project.return_value = mock_project
            
            with patch.object(parser, '_parse_file', return_value=[]):
                result = await parser.reparse_changed_file(project_id, "test.py")
                
                assert result["success"] is True
                assert result["symbols_extracted"] == 0
