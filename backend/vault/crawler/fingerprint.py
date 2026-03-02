"""Project fingerprinting and type detection logic."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from vault.config import settings
from vault.storage.models import ProjectType


class ProjectFingerprinter:
    """Analyzes directory structure to detect project type and characteristics."""

    def __init__(self) -> None:
        self.markers = settings.project_markers
        self.extensions = settings.language_extensions
        self.exclude_patterns = settings.exclude_patterns

    def detect_project_type(self, directory: Path) -> ProjectType:
        """Detect project type based on directory markers and files."""
        directory_str = str(directory)

        # Check for Unity projects
        if self._has_markers(directory, self.markers["unity"]):
            return ProjectType.UNITY

        # Check for Java projects
        if self._has_markers(directory, self.markers["java"]):
            return ProjectType.JAVA

        # Check for Python projects
        if self._has_markers(directory, self.markers["python"]):
            return ProjectType.PYTHON

        # Check for Node.js projects
        if self._has_markers(directory, self.markers["node"]):
            return ProjectType.NODE

        # Check for RenPy projects
        if self._has_markers(directory, self.markers["renpy"]):
            return ProjectType.RENPY

        # Check for C# projects
        if self._has_markers(directory, self.markers["csharp"]):
            return ProjectType.CSHARP

        # Default to other if no specific type detected
        return ProjectType.OTHER

    def get_primary_language(
        self, directory: Path, project_type: ProjectType
    ) -> Optional[str]:
        """Determine the primary programming language for a project."""
        extension_counts = self._count_file_extensions(directory)

        # Map project types to primary languages
        type_language_map = {
            ProjectType.UNITY: "csharp",
            ProjectType.JAVA: "java",
            ProjectType.PYTHON: "python",
            ProjectType.NODE: "javascript",
            ProjectType.RENPY: "renpy",
            ProjectType.CSHARP: "csharp",
        }

        # If we have a clear project type, use its primary language
        if project_type in type_language_map:
            primary = type_language_map[project_type]
            if extension_counts.get(primary, 0) > 0:
                return primary

        # Otherwise, find the language with the most files
        if extension_counts:
            return max(extension_counts.items(), key=lambda x: x[1])[0]

        return None

    def calculate_metrics(self, directory: Path) -> Tuple[int, int, Dict[str, int]]:
        """Calculate project metrics: file count, lines of code, language breakdown."""
        file_count = 0
        loc_total = 0
        language_counts: dict[str, int] = {}

        for root, dirs, files in os.walk(directory):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not self._should_exclude(Path(root) / d)]

            for file in files:
                file_path = Path(root) / file

                if self._should_exclude_file(file_path):
                    continue

                # Determine language by extension
                language = self._get_language_by_extension(file_path)
                if language:
                    file_count += 1
                    language_counts[language] = language_counts.get(language, 0) + 1

                    # Count lines of code (simple approximation)
                    try:
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            loc_total += sum(1 for _ in f if _.strip())
                    except (OSError, UnicodeDecodeError):
                        # Skip files that can't be read
                        continue

        return file_count, loc_total, language_counts

    def get_project_metadata(self, directory: Path) -> Dict:
        """Get comprehensive metadata about a project."""
        project_type = self.detect_project_type(directory)
        primary_language = self.get_primary_language(directory, project_type)
        file_count, loc_total, language_counts = self.calculate_metrics(directory)

        # Check for git repository
        has_git = (directory / ".git").exists()

        # Get timestamps
        timestamps = self._get_directory_timestamps(directory)

        return {
            "type": project_type,
            "language_primary": primary_language,
            "file_count": file_count,
            "loc_total": loc_total,
            "language_counts": language_counts,
            "git_has": has_git,
            "first_seen": timestamps.get("oldest"),
            "last_modified": timestamps.get("newest"),
        }

    def _has_markers(self, directory: Path, markers: List[str]) -> bool:
        """Check if directory contains any of the specified markers."""
        for marker in markers:
            if "*" in marker:
                # Handle wildcards
                if list(directory.glob(marker)):
                    return True
            else:
                # Handle exact paths
                marker_path = directory / marker
                if marker_path.exists():
                    return True
        return False

    def _count_file_extensions(self, directory: Path) -> Dict[str, int]:
        """Count files by programming language."""
        counts: dict[str, int] = {}

        for root, dirs, files in os.walk(directory):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not self._should_exclude(Path(root) / d)]

            for file in files:
                file_path = Path(root) / file

                if self._should_exclude_file(file_path):
                    continue

                language = self._get_language_by_extension(file_path)
                if language:
                    counts[language] = counts.get(language, 0) + 1

        return counts

    def _get_language_by_extension(self, file_path: Path) -> Optional[str]:
        """Get programming language by file extension."""
        suffix = file_path.suffix.lower()

        for language, extensions in self.extensions.items():
            if suffix in extensions:
                return language

        return None

    def _should_exclude(self, path: Path) -> bool:
        """Check if a directory should be excluded."""
        return any(pattern in path.name for pattern in self.exclude_patterns)

    def _should_exclude_file(self, file_path: Path) -> bool:
        """Check if a file should be excluded from analysis."""
        # Check if parent directory is excluded
        for parent in file_path.parents:
            if self._should_exclude(parent):
                return True

        # Check file extension
        if not self._get_language_by_extension(file_path):
            return True

        # Check file size (basic check)
        try:
            if file_path.stat().st_size > settings.max_file_size_mb * 1024 * 1024:
                return True
        except OSError:
            return True

        return False

    def _get_directory_timestamps(
        self, directory: Path
    ) -> Dict[str, Optional[datetime]]:
        """Get oldest and newest file timestamps in a directory."""
        oldest: Optional[datetime] = None
        newest: Optional[datetime] = None

        for root, dirs, files in os.walk(directory):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not self._should_exclude(Path(root) / d)]

            for file in files:
                file_path = Path(root) / file

                if self._should_exclude_file(file_path):
                    continue

                try:
                    mtime = datetime.fromtimestamp(
                        file_path.stat().st_mtime, timezone.utc
                    )

                    if oldest is None or mtime < oldest:
                        oldest = mtime

                    if newest is None or mtime > newest:
                        newest = mtime

                except OSError:
                    continue

        return {
            "oldest": oldest,
            "newest": newest,
        }
