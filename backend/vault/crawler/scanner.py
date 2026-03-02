"""Project scanner for discovering and analyzing development projects."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

from vault.config import settings
from vault.crawler.fingerprint import ProjectFingerprinter
from vault.storage.models import IndexStatus, Project, ProjectType
from vault.storage.repositories import ProjectRepository


class ProjectScanner:
    """Scans directories to discover and analyze development projects."""

    def __init__(self, project_repo: ProjectRepository) -> None:
        self.project_repo = project_repo
        self.fingerprinter = ProjectFingerprinter()

    async def scan_root_directories(
        self, root_paths: Optional[List[str]] = None
    ) -> List[Project]:
        """Scan all configured root directories for projects."""
        if not root_paths:
            root_paths = settings.root_directories

        if not root_paths:
            raise ValueError("No root directories configured for scanning")

        discovered_projects = []

        for root_path in root_paths:
            root = Path(root_path)
            if not root.exists():
                continue

            projects = await self._scan_directory(root)
            discovered_projects.extend(projects)

        return discovered_projects

    async def scan_directory(self, directory_path: str) -> List[Project]:
        """Scan a specific directory for projects."""
        directory = Path(directory_path)
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory_path}")

        return await self._scan_directory(directory)

    async def refresh_project(self, project_id: UUID) -> Optional[Project]:
        """Refresh an existing project's metadata."""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            return None

        # Update project metadata
        metadata = self.fingerprinter.get_project_metadata(Path(project.path))

        updated_project = await self.project_repo.update(project.id, **metadata)

        return updated_project

    async def _scan_directory(self, directory: Path) -> List[Project]:
        """Recursively scan a directory for projects."""
        projects = []

        # Get all immediate subdirectories that could be projects
        for item in directory.iterdir():
            if not item.is_dir():
                continue

            # Skip excluded directories
            if self._should_exclude_directory(item):
                continue

            # Check if this directory is a project
            if await self._is_project_directory(item):
                project = await self._create_or_update_project(item)
                if project:
                    projects.append(project)
            else:
                # Recursively scan subdirectories
                sub_projects = await self._scan_directory(item)
                projects.extend(sub_projects)

        return projects

    async def _is_project_directory(self, directory: Path) -> bool:
        """Determine if a directory contains a development project."""
        # Use fingerprinter to detect project type
        project_type = self.fingerprinter.detect_project_type(directory)

        # If it's not "other", we consider it a project
        if project_type != ProjectType.OTHER:
            return True

        # For "other" type, check if it has any code files
        file_count, _, _ = self.fingerprinter.calculate_metrics(directory)
        return file_count > 0

    async def _create_or_update_project(self, directory: Path) -> Optional[Project]:
        """Create a new project or update existing one."""
        try:
            # Check if project already exists
            existing_project = await self.project_repo.get_by_path(
                str(directory.absolute())
            )

            # Get project metadata
            metadata = self.fingerprinter.get_project_metadata(directory)

            if existing_project:
                # Update existing project
                updated_project = await self.project_repo.update(
                    existing_project.id, **metadata
                )
                return updated_project
            else:
                # Create new project
                project_data = {
                    "name": directory.name,
                    "path": str(directory.absolute()),
                    "index_status": IndexStatus.PENDING,
                    **metadata,
                }

                project = Project(**project_data)
                created_project = await self.project_repo.create(project)
                return created_project

        except Exception as e:
            # Log error but continue with other projects
            print(f"Error processing project {directory}: {e}")
            return None

    def _should_exclude_directory(self, directory: Path) -> bool:
        """Check if a directory should be excluded from scanning."""
        dir_name = directory.name.lower()

        # Check against exclude patterns
        for pattern in settings.exclude_patterns:
            if pattern.lower() in dir_name:
                return True

        # Skip hidden directories
        if dir_name.startswith("."):
            return True

        return False


class ProjectDiscoveryService:
    """High-level service for project discovery and management."""

    def __init__(self, project_repo: ProjectRepository) -> None:
        self.project_repo = project_repo
        self.scanner = ProjectScanner(project_repo)

    async def discover_all_projects(self) -> dict:
        """Discover all projects in configured directories."""
        discovered = await self.scanner.scan_root_directories()

        return {
            "success": True,
            "discovered_count": len(discovered),
            "projects": discovered,
        }

    async def scan_specific_path(self, path: str) -> dict:
        """Scan a specific path for projects."""
        try:
            discovered = await self.scanner.scan_directory(path)

            return {
                "success": True,
                "discovered_count": len(discovered),
                "projects": discovered,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "discovered_count": 0,
                "projects": [],
            }

    async def get_project_statistics(self) -> dict:
        """Get statistics about all discovered projects."""
        all_projects = await self.project_repo.get_all(limit=10000)  # Large limit

        stats = {
            "total_projects": len(all_projects),
            "by_type": {},
            "by_status": {},
            "total_files": 0,
            "total_loc": 0,
        }

        for project in all_projects:
            # Count by type
            project_type = (
                project.type.value if hasattr(project.type, "value") else project.type
            )
            stats["by_type"][project_type] = stats["by_type"].get(project_type, 0) + 1

            # Count by status
            status = (
                project.index_status.value
                if hasattr(project.index_status, "value")
                else project.index_status
            )
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # Aggregate metrics
            stats["total_files"] += project.file_count
            stats["total_loc"] += project.loc_total

        return stats
