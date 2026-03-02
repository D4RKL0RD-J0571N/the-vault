"""Tests for crawler layer (scanner and fingerprinting)."""

import pytest
from pathlib import Path
from uuid import uuid4

from vault.crawler.fingerprint import ProjectFingerprinter
from vault.crawler.scanner import ProjectScanner, ProjectDiscoveryService
from vault.storage.models import ProjectType, IndexStatus, Project
from vault.storage.repositories import ProjectRepository


class TestProjectFingerprinter:
    """Test cases for ProjectFingerprinter."""
    
    def test_detect_unity_project(self, temp_project_dir: Path):
        """Test detecting Unity projects."""
        # Create Unity project structure
        (temp_project_dir / "Assets").mkdir()
        (temp_project_dir / "ProjectSettings").mkdir()
        (temp_project_dir / "Assembly-CSharp.csproj").touch()
        
        fingerprinter = ProjectFingerprinter()
        project_type = fingerprinter.detect_project_type(temp_project_dir)
        
        assert project_type == ProjectType.UNITY
    
    def test_detect_java_project(self, temp_project_dir: Path):
        """Test detecting Java projects."""
        # Create Java project structure
        (temp_project_dir / "src" / "main" / "java").mkdir(parents=True)
        (temp_project_dir / "pom.xml").touch()
        (temp_project_dir / "src" / "main" / "java" / "Test.java").touch()
        
        fingerprinter = ProjectFingerprinter()
        project_type = fingerprinter.detect_project_type(temp_project_dir)
        
        assert project_type == ProjectType.JAVA
    
    def test_detect_python_project(self, temp_project_dir: Path):
        """Test detecting Python projects."""
        # Create Python project structure
        (temp_project_dir / "requirements.txt").touch()
        (temp_project_dir / "test.py").touch()
        
        fingerprinter = ProjectFingerprinter()
        project_type = fingerprinter.detect_project_type(temp_project_dir)
        
        assert project_type == ProjectType.PYTHON
    
    def test_detect_node_project(self, temp_project_dir: Path):
        """Test detecting Node.js projects."""
        # Create Node.js project structure
        (temp_project_dir / "package.json").touch()
        (temp_project_dir / "index.js").touch()
        
        fingerprinter = ProjectFingerprinter()
        project_type = fingerprinter.detect_project_type(temp_project_dir)
        
        assert project_type == ProjectType.NODE
    
    def test_detect_csharp_project(self, temp_project_dir: Path):
        """Test detecting C# projects."""
        # Create C# project structure
        (temp_project_dir / "TestProject.csproj").touch()
        (temp_project_dir / "Program.cs").touch()
        
        fingerprinter = ProjectFingerprinter()
        project_type = fingerprinter.detect_project_type(temp_project_dir)
        
        assert project_type == ProjectType.CSHARP
    
    def test_detect_renpy_project(self, temp_project_dir: Path):
        """Test detecting RenPy projects."""
        # Create RenPy project structure
        (temp_project_dir / "game").mkdir()
        (temp_project_dir / "game" / "script.rpy").touch()
        
        fingerprinter = ProjectFingerprinter()
        project_type = fingerprinter.detect_project_type(temp_project_dir)
        
        assert project_type == ProjectType.RENPY
    
    def test_detect_other_project(self, temp_project_dir: Path):
        """Test detecting projects as 'other' type."""
        # Create a project with no specific markers
        (temp_project_dir / "some_file.txt").touch()
        
        fingerprinter = ProjectFingerprinter()
        project_type = fingerprinter.detect_project_type(temp_project_dir)
        
        assert project_type == ProjectType.OTHER
    
    def test_get_primary_language(self, temp_project_dir: Path):
        """Test determining primary language."""
        # Create Python project
        (temp_project_dir / "requirements.txt").touch()
        (temp_project_dir / "test1.py").touch()
        (temp_project_dir / "test2.py").touch()
        (temp_project_dir / "README.md").touch()
        
        fingerprinter = ProjectFingerprinter()
        primary_language = fingerprinter.get_primary_language(temp_project_dir, ProjectType.PYTHON)
        
        assert primary_language == "python"
    
    def test_calculate_metrics(self, temp_project_dir: Path):
        """Test calculating project metrics."""
        # Create some files with content
        (temp_project_dir / "test1.py").write_text("def func1():\n    pass\n\ndef func2():\n    return 1")
        (temp_project_dir / "test2.py").write_text("class Test:\n    def method(self):\n        pass")
        (temp_project_dir / "README.md").write_text("# Test Project")
        
        fingerprinter = ProjectFingerprinter()
        file_count, loc_total, language_counts = fingerprinter.calculate_metrics(temp_project_dir)
        
        assert file_count == 2  # Only Python files counted
        assert loc_total == 7  # Lines of code in Python files
        assert language_counts.get("python", 0) == 2
    
    def test_get_project_metadata(self, temp_project_dir: Path):
        """Test getting comprehensive project metadata."""
        # Create Python project
        (temp_project_dir / "requirements.txt").touch()
        (temp_project_dir / "test.py").write_text("def test():\n    pass")
        (temp_project_dir / ".git").mkdir()
        
        fingerprinter = ProjectFingerprinter()
        metadata = fingerprinter.get_project_metadata(temp_project_dir)
        
        assert metadata["type"] == ProjectType.PYTHON
        assert metadata["language_primary"] == "python"
        assert metadata["file_count"] == 1
        assert metadata["loc_total"] == 2
        assert metadata["git_has"] is True
        assert "first_seen" in metadata
        assert "last_modified" in metadata


class TestProjectScanner:
    """Test cases for ProjectScanner."""
    
    @pytest.mark.asyncio
    async def test_scan_directory_with_projects(self, temp_project_dir: Path, project_repo: ProjectRepository):
        """Test scanning a directory containing multiple projects."""
        # Create multiple projects
        python_dir = temp_project_dir / "python_project"
        java_dir = temp_project_dir / "java_project"
        
        python_dir.mkdir()
        java_dir.mkdir()
        
        # Python project
        (python_dir / "requirements.txt").touch()
        (python_dir / "test.py").touch()
        
        # Java project
        (java_dir / "pom.xml").touch()
        (java_dir / "src" / "main" / "java").mkdir(parents=True)
        (java_dir / "src" / "main" / "java" / "Test.java").touch()
        
        scanner = ProjectScanner(project_repo)
        projects = await scanner.scan_directory(str(temp_project_dir))
        
        assert len(projects) == 2
        
        project_names = {p.name for p in projects}
        assert "python_project" in project_names
        assert "java_project" in project_names
        
        project_types = {p.type for p in projects}
        assert ProjectType.PYTHON in project_types
        assert ProjectType.JAVA in project_types
    
    @pytest.mark.asyncio
    async def test_scan_empty_directory(self, temp_project_dir: Path, project_repo: ProjectRepository):
        """Test scanning an empty directory."""
        scanner = ProjectScanner(project_repo)
        projects = await scanner.scan_directory(str(temp_project_dir))
        
        assert len(projects) == 0
    
    @pytest.mark.asyncio
    async def test_scan_nonexistent_directory(self, project_repo: ProjectRepository):
        """Test scanning a non-existent directory."""
        scanner = ProjectScanner(project_repo)
        
        with pytest.raises(ValueError, match="Directory does not exist"):
            await scanner.scan_directory("/nonexistent/path")


class TestProjectDiscoveryService:
    """Test cases for ProjectDiscoveryService."""
    
    @pytest.mark.asyncio
    async def test_discover_all_projects(self, temp_project_dir: Path, project_repo: ProjectRepository):
        """Test discovering all projects in configured directories."""
        # Create test projects
        python_dir = temp_project_dir / "python_project"
        python_dir.mkdir()
        (python_dir / "requirements.txt").touch()
        (python_dir / "test.py").touch()
        
        service = ProjectDiscoveryService(project_repo)
        
        # Mock the root directories to use our temp directory
        from vault.config import settings
        original_roots = settings.root_directories
        settings.root_directories = [str(temp_project_dir)]
        
        try:
            result = await service.discover_all_projects()
            
            assert result["success"] is True
            assert result["discovered_count"] == 1
            assert len(result["projects"]) == 1
            assert result["projects"][0].name == "python_project"
            assert result["projects"][0].type == ProjectType.PYTHON
        
        finally:
            # Restore original settings
            settings.root_directories = original_roots
    
    @pytest.mark.asyncio
    async def test_scan_specific_path(self, temp_project_dir: Path, project_repo: ProjectRepository):
        """Test scanning a specific path."""
        # Create test project
        python_dir = temp_project_dir / "python_project"
        python_dir.mkdir()
        (python_dir / "requirements.txt").touch()
        (python_dir / "test.py").touch()
        
        service = ProjectDiscoveryService(project_repo)
        result = await service.scan_specific_path(str(temp_project_dir))
        
        assert result["success"] is True
        assert result["discovered_count"] == 1
        assert len(result["projects"]) == 1
    
    @pytest.mark.asyncio
    async def test_scan_nonexistent_path(self, project_repo: ProjectRepository):
        """Test scanning a non-existent path."""
        service = ProjectDiscoveryService(project_repo)
        result = await service.scan_specific_path("/nonexistent/path")
        
        assert result["success"] is False
        assert "error" in result
        assert result["discovered_count"] == 0
    
    @pytest.mark.asyncio
    async def test_get_project_statistics(self, temp_project_dir: Path, project_repo: ProjectRepository):
        """Test getting project statistics."""
        # Create test projects
        python_dir = temp_project_dir / "python_project"
        java_dir = temp_project_dir / "java_project"
        
        python_dir.mkdir()
        java_dir.mkdir()
        
        # Python project
        (python_dir / "requirements.txt").touch()
        (python_dir / "test.py").write_text("def test():\n    pass")
        
        # Java project
        (java_dir / "pom.xml").touch()
        (java_dir / "src" / "main" / "java").mkdir(parents=True)
        (java_dir / "src" / "main" / "java" / "Test.java").write_text("public class Test {}")
        
        # Create projects in database
        from vault.crawler.fingerprint import ProjectFingerprinter
        fingerprinter = ProjectFingerprinter()
        
        for project_dir in [python_dir, java_dir]:
            metadata = fingerprinter.get_project_metadata(project_dir)
            project = Project(
                id=uuid4(),
                name=project_dir.name,
                path=str(project_dir),
                index_status=IndexStatus.COMPLETE,
                **metadata
            )
            await project_repo.create(project)
        
        service = ProjectDiscoveryService(project_repo)
        stats = await service.get_project_statistics()
        
        assert stats["total_projects"] == 2
        assert stats["by_type"][ProjectType.PYTHON.value] == 1
        assert stats["by_type"][ProjectType.JAVA.value] == 1
        assert stats["by_status"][IndexStatus.COMPLETE.value] == 2
        assert stats["total_files"] == 2
        assert stats["total_loc"] == 3  # 2 lines Python + 1 line Java
