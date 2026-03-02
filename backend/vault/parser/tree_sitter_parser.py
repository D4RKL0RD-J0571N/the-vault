"""Main tree-sitter parser coordinator for The Vault."""

import asyncio
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID

from vault.config import settings
from vault.crawler.fingerprint import ProjectFingerprinter
from vault.exceptions import ParsingError
from vault.parser.extractors import get_extractor
from vault.storage.models import IndexStatus
from vault.storage.models import Project
from vault.storage.models import Symbol
from vault.storage.repositories import ProjectRepository
from vault.storage.repositories import SymbolRepository


class TreeSitterParser:
    """Main parser that coordinates symbol extraction across projects."""

    def __init__(
        self, project_repo: ProjectRepository, symbol_repo: SymbolRepository
    ) -> None:
        self.project_repo = project_repo
        self.symbol_repo = symbol_repo
        self.fingerprinter = ProjectFingerprinter()

    async def parse_project(self, project_id: UUID) -> Dict:
        """Parse all files in a project and extract symbols."""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        try:
            # Update project status to parsing
            await self.project_repo.update_status(project_id, IndexStatus.PARSING)

            # Clear existing symbols for this project
            await self.symbol_repo.delete_by_project(project_id)

            # Get all code files in the project
            files = await self._get_project_files(project)

            # Parse each file and extract symbols
            all_symbols = []
            for file_path in files:
                try:
                    symbols = await self._parse_file(file_path, project_id)
                    all_symbols.extend(symbols)
                except ParsingError as e:
                    # Log error but continue with other files
                    print(f"Error parsing {file_path}: {e}")
                    continue

            # Batch insert symbols
            if all_symbols:
                await self.symbol_repo.create_batch(all_symbols)

            # Update project status to complete
            await self.project_repo.update_status(project_id, IndexStatus.COMPLETE)

            return {
                "success": True,
                "project_id": project_id,
                "files_parsed": len(files),
                "symbols_extracted": len(all_symbols),
                "errors": 0,
            }

        except Exception as e:
            # Update project status to error
            await self.project_repo.update_status(project_id, IndexStatus.ERROR)

            return {
                "success": False,
                "project_id": project_id,
                "error": str(e),
                "files_parsed": 0,
                "symbols_extracted": 0,
                "errors": 1,
            }

    async def parse_file(self, project_id: UUID, file_path: str) -> List[Symbol]:
        """Parse a single file and extract symbols."""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        full_path = Path(project.path) / file_path
        return await self._parse_file(full_path, project_id)

    async def reparse_changed_file(self, project_id: UUID, file_path: str) -> Dict:
        """Reparse a file that has changed."""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        try:
            # Delete existing symbols for this file
            await self.symbol_repo.delete_by_file(project_id, file_path)

            # Parse the file
            full_path = Path(project.path) / file_path
            symbols = await self._parse_file(full_path, project_id)

            # Insert new symbols
            if symbols:
                await self.symbol_repo.create_batch(symbols)

            return {
                "success": True,
                "file_path": file_path,
                "symbols_extracted": len(symbols),
            }

        except Exception as e:
            return {
                "success": False,
                "file_path": file_path,
                "error": str(e),
                "symbols_extracted": 0,
            }

    async def get_parsing_statistics(self, project_id: UUID) -> Dict:
        """Get parsing statistics for a project."""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Get all symbols for the project
        symbols = await self.symbol_repo.get_by_project(project_id)

        # Count by type
        symbol_counts: dict[str, int] = {}
        todo_count = 0

        for symbol in symbols:
            symbol_type = getattr(symbol.symbol_type, "value", symbol.symbol_type)
            symbol_counts[symbol_type] = symbol_counts.get(symbol_type, 0) + 1

            if symbol.has_todo:
                todo_count += 1

        return {
            "project_id": project_id,
            "project_name": project.name,
            "total_symbols": len(symbols),
            "symbol_counts": symbol_counts,
            "todo_count": todo_count,
            "last_parsed": project.updated_at,
        }

    async def _get_project_files(self, project: Project) -> List[Path]:
        """Get all code files in a project."""
        import os

        project_path = Path(project.path)
        files = []

        for root, dirs, filenames in os.walk(project_path):
            # Skip excluded directories
            dirs[:] = [
                d for d in dirs if not self._should_exclude_directory(Path(root) / d)
            ]

            for filename in filenames:
                file_path = Path(root) / filename
                if self._should_include_file(file_path):
                    files.append(file_path)

        return files

    async def _parse_file(self, file_path: Path, project_id: UUID) -> List[Symbol]:
        """Parse a single file and extract symbols."""
        # Determine language by extension
        language = self.fingerprinter._get_language_by_extension(file_path)
        if not language:
            return []

        # Get appropriate extractor
        extractor = get_extractor(language)

        # Extract symbols
        symbols = extractor.extract_symbols(file_path, str(project_id))

        return symbols

    def _should_exclude_directory(self, dir_path: Path) -> bool:
        """Check if a directory should be excluded."""
        dir_name = dir_path.name.lower()

        for pattern in settings.exclude_patterns:
            if pattern.lower() in dir_name:
                return True

        return dir_name.startswith(".")

    def _should_include_file(self, file_path: Path) -> bool:
        """Check if a file should be included in parsing."""
        # Check if it's a code file
        language = self.fingerprinter._get_language_by_extension(file_path)
        if not language:
            return False

        # Check file size
        try:
            if file_path.stat().st_size > settings.max_file_size_mb * 1024 * 1024:
                return False
        except OSError:
            return False

        return True


class ParsingService:
    """High-level service for managing parsing operations."""

    def __init__(
        self, project_repo: ProjectRepository, symbol_repo: SymbolRepository
    ) -> None:
        self.project_repo = project_repo
        self.symbol_repo = symbol_repo
        self.parser = TreeSitterParser(project_repo, symbol_repo)
        self._active_tasks: Dict[UUID, asyncio.Task] = {}

    async def start_parsing_project(self, project_id: UUID) -> Dict:
        """Start parsing a project in the background."""
        if project_id in self._active_tasks:
            return {
                "success": False,
                "message": "Project is already being parsed",
                "project_id": project_id,
            }

        # Verify project exists
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            return {
                "success": False,
                "message": f"Project {project_id} not found",
                "project_id": project_id,
            }

        # Create background task
        task = asyncio.create_task(self.parser.parse_project(project_id))
        self._active_tasks[project_id] = task

        # Add callback to clean up when done
        task.add_done_callback(lambda t: self._active_tasks.pop(project_id, None))

        return {
            "success": True,
            "message": "Parsing started",
            "project_id": project_id,
        }

    async def get_parsing_status(self, project_id: UUID) -> Dict:
        """Get the parsing status of a project."""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            return {
                "success": False,
                "error": "Project not found",
            }

        is_active = project_id in self._active_tasks

        return {
            "success": True,
            "project_id": project_id,
            "status": getattr(project.index_status, "value", project.index_status),
            "is_parsing": is_active,
        }

    async def cancel_parsing(self, project_id: UUID) -> Dict:
        """Cancel an active parsing task."""
        if project_id not in self._active_tasks:
            return {
                "success": False,
                "message": "No active parsing task for this project",
            }

        task = self._active_tasks[project_id]
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Update project status
        await self.project_repo.update_status(project_id, IndexStatus.PENDING)

        return {
            "success": True,
            "message": "Parsing cancelled",
            "project_id": project_id,
        }

    async def get_active_parsing_tasks(self) -> List[UUID]:
        """Get list of projects currently being parsed."""
        return list(self._active_tasks.keys())

    async def parse_multiple_projects(self, project_ids: List[UUID]) -> Dict:
        """Parse multiple projects concurrently."""
        tasks = []

        for project_id in project_ids:
            if project_id not in self._active_tasks:
                task = asyncio.create_task(self.parser.parse_project(project_id))
                self._active_tasks[project_id] = task
                task.add_done_callback(
                    lambda t: self._active_tasks.pop(project_id, None)
                )
                tasks.append(task)

        if not tasks:
            return {
                "success": True,
                "message": "No projects to parse (none provided or all already being parsed)",
                "projects_attempted": 0,
                "successful": 0,
                "failed": 0,
            }

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful = 0
        failed = 0

        for result in results:
            if isinstance(result, Exception):
                failed += 1
            elif isinstance(result, dict) and result.get("success", False):
                successful += 1
            else:
                failed += 1

        return {
            "success": True,
            "projects_attempted": len(tasks),
            "successful": successful,
            "failed": failed,
        }
