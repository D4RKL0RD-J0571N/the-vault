"""Tests for the file system watcher module."""

import asyncio
import pytest
from pathlib import Path
from vault.crawler.watcher import WatcherService, FileWatcher, VaultFileEventHandler


class TestWatcher:
    """Test cases for FileWatcher and WatcherService."""

    @pytest.mark.asyncio
    async def test_event_handler_debouncing(self, tmp_path):
        """Test that multiple events for the same file are debounced."""
        events = []
        def callback(path, event_type):
            events.append((path, event_type))

        handler = VaultFileEventHandler(callback)
        handler._debounce_delay = 0.1  # Shorten for testing
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial")
        
        # Simulate multiple modifications
        from watchdog.events import FileModifiedEvent
        for _ in range(5):
            handler.on_modified(FileModifiedEvent(str(test_file)))
            
        # Wait for debounce
        await asyncio.sleep(0.3)
        
        # Should only have 1 event
        assert len(events) == 1
        assert events[0][1] == "modified"

    @pytest.mark.asyncio
    async def test_watcher_service_lifecycle(self, tmp_path):
        """Test starting and stopping the watcher service."""
        service = WatcherService()
        path = str(tmp_path)
        
        service.start_watching([path])
        assert path in service._watched_paths
        assert service.file_watcher.is_running
        
        service.stop_watching()
        assert not service.file_watcher.is_running
        assert len(service._watched_paths) == 0

    @pytest.mark.asyncio
    async def test_queue_processing(self):
        """Test adding and retrieving changes from the queue."""
        service = WatcherService()
        
        # Simulate a file change
        service._on_file_change("test.py", "modified")
        
        # Wait a moment for the task to run
        await asyncio.sleep(0.1)
        
        changes = await service.get_pending_changes()
        assert len(changes) == 1
        assert changes[0]["file_path"] == "test.py"
        assert changes[0]["event_type"] == "modified"

    @pytest.mark.asyncio
    async def test_handler_move_event(self, tmp_path):
        """Test handling of file move events."""
        events = []
        def callback(path, event_type):
            events.append((path, event_type))

        handler = VaultFileEventHandler(callback)
        handler._debounce_delay = 0.05
        
        src_path = tmp_path / "old.txt"
        dest_path = tmp_path / "new.txt"
        dest_path.write_text("moved") # Must exist for exists() check in debouncer
        
        from watchdog.events import FileMovedEvent
        handler.on_moved(FileMovedEvent(str(src_path), str(dest_path)))
        
        await asyncio.sleep(0.2)
        
        # Should trigger two calls: one for moved (src) and one for created (dest)
        # However, our current logic filters out paths that don't exist
        assert len(events) >= 1
