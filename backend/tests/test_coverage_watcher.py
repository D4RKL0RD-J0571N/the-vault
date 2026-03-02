"""Tests for vault.crawler.watcher to improve coverage."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from watchdog.events import FileSystemEvent

from vault.crawler.watcher import (
    VaultFileEventHandler, 
    FileWatcher, 
    ProjectChangeQueue, 
    WatcherService
)

from watchdog.events import FileSystemEvent, FileCreatedEvent, FileDeletedEvent, FileMovedEvent, FileModifiedEvent

@pytest.mark.asyncio
async def test_vault_file_event_handler():
    callback = MagicMock()
    handler = VaultFileEventHandler(callback)
    handler._debounce_delay = 0.001  # Fast for tests
    
    # Test created
    created_event = FileCreatedEvent("test.py")
    with patch("vault.crawler.watcher.Path.exists", return_value=True):
        handler.on_created(created_event)
        await asyncio.sleep(0.01)
        callback.assert_called_with("test.py", "created")
    
    # Test modified
    modified_event = FileModifiedEvent("test.py")
    with patch("vault.crawler.watcher.Path.exists", return_value=True):
        handler.on_modified(modified_event)
        await asyncio.sleep(0.01)
        callback.assert_called_with("test.py", "modified")

    # Test deleted
    deleted_event = FileDeletedEvent("test.py")
    handler.on_deleted(deleted_event)
    await asyncio.sleep(0.01)
    
    # Test moved
    moved_event = FileMovedEvent("old.py", "new.py")
    with patch("vault.crawler.watcher.Path.exists", return_value=True):
        handler.on_moved(moved_event)
        await asyncio.sleep(0.01)
        # moved triggers creator on dest_path too
        callback.assert_any_call("new.py", "created")

@pytest.mark.asyncio
async def test_file_watcher_paths():
    watcher = FileWatcher()
    callback = MagicMock()
    
    # Mock Observer.schedule to avoid real FS watching
    with patch.object(watcher.observer, "schedule"):
        with patch.object(watcher.observer, "start"):
            # Test start_watching with non-existent path
            watcher.start_watching(["/non/existent"], callback)
            assert "/non/existent" not in watcher.handlers
            
            # Test add_path
            with patch("vault.crawler.watcher.Path.exists", return_value=True):
                watcher.add_path("/some/path", callback)
                assert "/some/path" in watcher.handlers
                
                # add_path while running
                watcher.is_running = True
                watcher.add_path("/new/path", callback)
                assert "/new/path" in watcher.handlers
    
    # Test remove_path
    watcher.remove_path("/some/path")
    assert "/some/path" not in watcher.handlers
    watcher.remove_path("/invalid") # Should not crash
    
    # Test stop_watching
    watcher.is_running = True
    with patch.object(watcher.observer, "stop"):
        with patch.object(watcher.observer, "join"):
            watcher.stop_watching()
            assert watcher.is_running is False
            assert len(watcher.handlers) == 0

@pytest.mark.asyncio
async def test_project_change_queue():
    queue = ProjectChangeQueue()
    
    await queue.add_change("f1.py", "modified")
    assert queue.size() == 1
    assert not queue.empty()
    
    change = await queue.get_next_change()
    assert change["file_path"] == "f1.py"
    
    # Test clear
    await queue.add_change("f2.py", "created")
    await queue.add_change("f3.py", "deleted")
    assert queue.size() == 2
    await queue.clear()
    assert queue.empty()
    assert queue.size() == 0

@pytest.mark.asyncio
async def test_watcher_service_branches():
    service = WatcherService()
    
    # Start watching some paths
    with patch.object(service.file_watcher, "start_watching") as mock_start:
        with patch("vault.crawler.watcher.Path.exists", return_value=True):
            service.start_watching(["/p1", "/p2"])
            mock_start.assert_called_once()
            
            # Start watching same paths (no new paths)
            mock_start.reset_mock()
            service.start_watching(["/p1"])
            mock_start.assert_not_called()

    # on_file_change
    with patch.object(service.change_queue, "add_change", new_callable=AsyncMock) as mock_add:
        service._on_file_change("f.py", "created")
        # Ensure the task is created (we can't easily wait for it if we don't have the task handle,
        # but we can check if add_change was called since create_task runs it)
        # Actually, create_task might not run it immediately.
        await asyncio.sleep(0.01)
        mock_add.assert_called_once_with("f.py", "created")

    # get_pending_changes
    await service.change_queue.add_change("f.py", "modified")
    changes = await service.get_pending_changes()
    assert len(changes) == 1
    
    # Stop watching
    service.stop_watching()
    assert len(service._watched_paths) == 0
    
    # Test if is_running branches
    service.file_watcher.is_running = False
    service.file_watcher.stop_watching() # Hit 97 branch

@pytest.mark.asyncio
async def test_watcher_extra_edge_cases():
    watcher = FileWatcher()
    
    # Hit 107 in add_path
    with patch("vault.crawler.watcher.Path.exists", return_value=False):
        watcher.add_path("/non/existent/again", MagicMock())
        assert "/non/existent/again" not in watcher.handlers

    # Hit 158-159 in ProjectChangeQueue.clear
    queue = ProjectChangeQueue()
    await queue.add_change("test.py", "modified")
    # Mock get_nowait to raise Empty after first call
    orig_gnw = queue._queue.get_nowait
    def side_effect():
        queue._queue.task_done() # Cleanup internal state if needed
        # In this simple case we just want to hit the except block
        raise asyncio.QueueEmpty()
    
    # Actually it's easier to just call clear when it's empty but that doesn't hit the except block 
    # unless it's empty during the loop
    # Let's just call it when empty
    await queue.clear() # Hit 155 branch

    # Hit watcher.start_watching already running
    watcher.is_running = True
    watcher.start_watching([], MagicMock()) # Hit 91 exit
    
@pytest.mark.asyncio
async def test_watcher_service_changes_limit():
    service = WatcherService()
    # Add 105 changes
    for i in range(105):
        await service.change_queue.add_change(f"f{i}.py", "modified")
    
    changes = await service.get_pending_changes()
    assert len(changes) == 100
    
    changes2 = await service.get_pending_changes()
    assert len(changes2) == 5
