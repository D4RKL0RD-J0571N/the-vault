"""File system watcher for monitoring project changes."""

import asyncio
from pathlib import Path
from typing import Callable, Set

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from vault.config import settings


class VaultFileEventHandler(FileSystemEventHandler):
    """File system event handler for The Vault."""

    def __init__(self, callback: Callable[[str, str], None]) -> None:
        super().__init__()
        self.callback = callback
        self._debounce_delay = 1.0  # seconds
        self._pending_events: Set[str] = set()
        self._debounce_task: asyncio.Task | None = None

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if not event.is_directory:
            self._schedule_callback(event.src_path, "modified")

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if not event.is_directory:
            self._schedule_callback(event.src_path, "created")

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        if not event.is_directory:
            self._schedule_callback(event.src_path, "deleted")

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move/rename events."""
        if not event.is_directory:
            self._schedule_callback(event.src_path, "moved")
            self._schedule_callback(event.dest_path, "created")

    def _schedule_callback(self, file_path: str, event_type: str) -> None:
        """Schedule a callback with debouncing."""
        self._pending_events.add(file_path)

        # Cancel existing debounce task
        if self._debounce_task:
            self._debounce_task.cancel()

        # Schedule new debounce task
        self._debounce_task = asyncio.create_task(self._debounce_callback(event_type))

    async def _debounce_callback(self, event_type: str) -> None:
        """Execute callback after debounce delay."""
        await asyncio.sleep(self._debounce_delay)

        # Process all pending events
        for file_path in self._pending_events:
            if Path(file_path).exists():  # Only process if file still exists
                self.callback(file_path, event_type)

        # Clear pending events
        self._pending_events.clear()


class FileWatcher:
    """File system watcher for monitoring project changes."""

    def __init__(self) -> None:
        self.observer = Observer()
        self.handlers: dict[str, VaultFileEventHandler] = {}
        self.is_running = False

    def start_watching(
        self, paths: list[str], callback: Callable[[str, str], None]
    ) -> None:
        """Start watching the specified paths."""
        for path_str in paths:
            path = Path(path_str)
            if not path.exists():
                continue

            # Create handler for this path
            handler = VaultFileEventHandler(callback)
            self.handlers[path_str] = handler

            # Start watching
            self.observer.schedule(handler, str(path), recursive=True)

        if not self.is_running:
            self.observer.start()
            self.is_running = True

    def stop_watching(self) -> None:
        """Stop watching all paths."""
        if self.is_running:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            self.handlers.clear()

    def add_path(self, path: str, callback: Callable[[str, str], None]) -> None:
        """Add a new path to watch."""
        path_obj = Path(path)
        if not path_obj.exists():
            return

        handler = VaultFileEventHandler(callback)
        self.handlers[path] = handler

        if self.is_running:
            self.observer.schedule(handler, path, recursive=True)

    def remove_path(self, path: str) -> None:
        """Remove a path from watching."""
        if path in self.handlers:
            # Note: watchdog doesn't support unscheduling specific paths easily
            # For now, we'll just remove the handler reference
            del self.handlers[path]


class ProjectChangeQueue:
    """Queue for managing project file changes."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._processing = False

    async def add_change(self, file_path: str, event_type: str) -> None:
        """Add a file change to the queue."""
        await self._queue.put(
            {
                "file_path": file_path,
                "event_type": event_type,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

    async def get_next_change(self) -> dict | None:
        """Get the next file change from the queue."""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    def size(self) -> int:
        """Get the current queue size."""
        return self._queue.qsize()

    def empty(self) -> bool:
        """Check if the queue is empty."""
        return self._queue.empty()

    async def clear(self) -> None:
        """Clear all items from the queue."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break


class WatcherService:
    """High-level service for file system watching."""

    def __init__(self) -> None:
        self.file_watcher = FileWatcher()
        self.change_queue = ProjectChangeQueue()
        self._watched_paths: Set[str] = set()

    def start_watching(self, paths: list[str]) -> None:
        """Start watching the specified paths."""
        # Filter out paths we're already watching
        new_paths = [p for p in paths if p not in self._watched_paths]

        if new_paths:
            self.file_watcher.start_watching(new_paths, self._on_file_change)
            self._watched_paths.update(new_paths)

    def stop_watching(self) -> None:
        """Stop watching all paths."""
        self.file_watcher.stop_watching()
        self._watched_paths.clear()

    async def get_pending_changes(self) -> list[dict]:
        """Get all pending file changes."""
        changes = []

        # Process up to 100 changes at a time to avoid blocking
        for _ in range(100):
            change = await self.change_queue.get_next_change()
            if change is None:
                break
            changes.append(change)

        return changes

    def _on_file_change(self, file_path: str, event_type: str) -> None:
        """Handle file system events."""
        # Add change to queue for processing
        asyncio.create_task(self.change_queue.add_change(file_path, event_type))
