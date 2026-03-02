"""Tests for storage layer (models and repositories)."""

import pytest
from uuid import uuid4

from vault.exceptions import ProjectNotFoundError, SymbolNotFoundError
from vault.storage.models import Project, Symbol, ProjectType, IndexStatus, SymbolType
from vault.storage.repositories import ProjectRepository, SymbolRepository


class TestProjectRepository:
    """Test cases for ProjectRepository."""
    
    @pytest.mark.asyncio
    async def test_create_project(self, project_repo: ProjectRepository, sample_project: Project):
        """Test creating a project."""
        created_project = await project_repo.create(sample_project)
        
        assert str(created_project.id) == str(sample_project.id)
        assert created_project.name == sample_project.name
        assert created_project.path == sample_project.path
        assert created_project.type == sample_project.type
    
    @pytest.mark.asyncio
    async def test_get_project_by_id(self, project_repo: ProjectRepository, sample_project: Project):
        """Test getting a project by ID."""
        await project_repo.create(sample_project)
        
        retrieved_project = await project_repo.get_by_id(sample_project.id)
        
        assert retrieved_project is not None
        assert str(retrieved_project.id) == str(sample_project.id)
        assert retrieved_project.name == sample_project.name
    
    @pytest.mark.asyncio
    async def test_get_project_by_path(self, project_repo: ProjectRepository, sample_project: Project):
        """Test getting a project by path."""
        await project_repo.create(sample_project)
        
        retrieved_project = await project_repo.get_by_path(sample_project.path)
        
        assert retrieved_project is not None
        assert retrieved_project.path == sample_project.path
    
    @pytest.mark.asyncio
    async def test_get_all_projects(self, project_repo: ProjectRepository):
        """Test getting all projects."""
        projects = []
        for i in range(5):
            project = Project(
                id=uuid4(),
                name=f"Project{i}",
                path=f"/test/project{i}",
                type=ProjectType.PYTHON,
            )
            projects.append(project)
            await project_repo.create(project)
        
        all_projects = await project_repo.get_all()
        
        assert len(all_projects) == 5
        for project in all_projects:
            assert project.name.startswith("Project")
    
    @pytest.mark.asyncio
    async def test_update_project(self, project_repo: ProjectRepository, sample_project: Project):
        """Test updating a project."""
        await project_repo.create(sample_project)
        
        updated_project = await project_repo.update(
            sample_project.id,
            name="UpdatedProject",
            loc_total=200,
        )
        
        assert updated_project.name == "UpdatedProject"
        assert updated_project.loc_total == 200
        assert updated_project.type == sample_project.type  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_project(self, project_repo: ProjectRepository):
        """Test updating a non-existent project."""
        with pytest.raises(ProjectNotFoundError):
            await project_repo.update(uuid4(), name="Test")
    
    @pytest.mark.asyncio
    async def test_delete_project(self, project_repo: ProjectRepository, sample_project: Project):
        """Test deleting a project."""
        await project_repo.create(sample_project)
        
        success = await project_repo.delete(sample_project.id)
        
        assert success is True
        
        # Verify it's gone
        retrieved_project = await project_repo.get_by_id(sample_project.id)
        assert retrieved_project is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_project(self, project_repo: ProjectRepository):
        """Test deleting a non-existent project."""
        success = await project_repo.delete(uuid4())
        assert success is False
    
    @pytest.mark.asyncio
    async def test_get_projects_by_type(self, project_repo: ProjectRepository):
        """Test getting projects by type."""
        python_project = Project(
            id=uuid4(),
            name="PythonProject",
            path="/test/python",
            type=ProjectType.PYTHON,
        )
        java_project = Project(
            id=uuid4(),
            name="JavaProject",
            path="/test/java",
            type=ProjectType.JAVA,
        )
        
        await project_repo.create(python_project)
        await project_repo.create(java_project)
        
        python_projects = await project_repo.get_by_type(ProjectType.PYTHON)
        java_projects = await project_repo.get_by_type(ProjectType.JAVA)
        
        assert len(python_projects) == 1
        assert python_projects[0].type == ProjectType.PYTHON
        assert len(java_projects) == 1
        assert java_projects[0].type == ProjectType.JAVA
    
    @pytest.mark.asyncio
    async def test_get_projects_by_status(self, project_repo: ProjectRepository):
        """Test getting projects by status."""
        pending_project = Project(
            id=uuid4(),
            name="PendingProject",
            path="/test/pending",
            type=ProjectType.PYTHON,
            index_status=IndexStatus.PENDING,
        )
        complete_project = Project(
            id=uuid4(),
            name="CompleteProject",
            path="/test/complete",
            type=ProjectType.PYTHON,
            index_status=IndexStatus.COMPLETE,
        )
        
        await project_repo.create(pending_project)
        await project_repo.create(complete_project)
        
        pending_projects = await project_repo.get_by_status(IndexStatus.PENDING)
        complete_projects = await project_repo.get_by_status(IndexStatus.COMPLETE)
        
        assert len(pending_projects) == 1
        assert pending_projects[0].index_status == IndexStatus.PENDING
        assert len(complete_projects) == 1
        assert complete_projects[0].index_status == IndexStatus.COMPLETE


class TestSymbolRepository:
    """Test cases for SymbolRepository."""
    
    @pytest.mark.asyncio
    async def test_create_symbol(self, symbol_repo: SymbolRepository, sample_symbol: Symbol):
        """Test creating a symbol."""
        created_symbol = await symbol_repo.create(sample_symbol)
        
        assert str(created_symbol.id) == str(sample_symbol.id)
        assert created_symbol.name == sample_symbol.name
        assert created_symbol.symbol_type == sample_symbol.symbol_type
    
    @pytest.mark.asyncio
    async def test_create_batch_symbols(self, symbol_repo: SymbolRepository):
        """Test creating multiple symbols in batch."""
        project_id = uuid4()
        symbols = []
        
        for i in range(5):
            symbol = Symbol(
                id=uuid4(),
                project_id=project_id,
                file_path=f"test{i}.py",
                symbol_type=SymbolType.FUNCTION,
                name=f"function_{i}",
                qualified_name=f"function_{i}",
                line_start=i + 1,
                line_end=i + 5,
                content_hash=f"hash{i}",
            )
            symbols.append(symbol)
        
        created_symbols = await symbol_repo.create_batch(symbols)
        
        assert len(created_symbols) == 5
        for symbol in created_symbols:
            # Convert both to string for comparison since UUIDs are stored as strings in SQLite
            assert str(symbol.project_id) == str(project_id)
    
    @pytest.mark.asyncio
    async def test_get_symbol_by_id(self, symbol_repo: SymbolRepository, sample_symbol: Symbol):
        """Test getting a symbol by ID."""
        await symbol_repo.create(sample_symbol)
        
        retrieved_symbol = await symbol_repo.get_by_id(sample_symbol.id)
        
        assert retrieved_symbol is not None
        assert str(retrieved_symbol.id) == str(sample_symbol.id)
        assert retrieved_symbol.name == sample_symbol.name
    
    @pytest.mark.asyncio
    async def test_get_symbols_by_project(self, symbol_repo: SymbolRepository):
        """Test getting symbols by project."""
        project_id = uuid4()
        symbols = []
        
        # Create symbols for the project
        for i in range(3):
            symbol = Symbol(
                id=uuid4(),
                project_id=project_id,
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=f"function_{i}",
                qualified_name=f"function_{i}",
                line_start=i + 1,
                line_end=i + 5,
                content_hash=f"hash{i}",
            )
            symbols.append(symbol)
            await symbol_repo.create(symbol)
        
        # Create symbols for another project
        other_project_id = uuid4()
        other_symbol = Symbol(
            id=uuid4(),
            project_id=other_project_id,
            file_path="other.py",
            symbol_type=SymbolType.FUNCTION,
            name="other_function",
            qualified_name="other_function",
            line_start=1,
            line_end=5,
            content_hash="other_hash",
        )
        await symbol_repo.create(other_symbol)
        
        # Get symbols for the first project
        project_symbols = await symbol_repo.get_by_project(project_id)
        
        assert len(project_symbols) == 3
        for symbol in project_symbols:
            # Convert both to string for comparison since UUIDs are stored as strings in SQLite
            assert str(symbol.project_id) == str(project_id)
    
    @pytest.mark.asyncio
    async def test_get_symbols_by_type(self, symbol_repo: SymbolRepository):
        """Test getting symbols by type."""
        project_id = uuid4()
        
        # Create function symbols
        for i in range(2):
            symbol = Symbol(
                id=uuid4(),
                project_id=project_id,
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=f"function_{i}",
                qualified_name=f"function_{i}",
                line_start=i + 1,
                line_end=i + 5,
                content_hash=f"hash{i}",
            )
            await symbol_repo.create(symbol)
        
        # Create class symbols
        for i in range(3):
            symbol = Symbol(
                id=uuid4(),
                project_id=project_id,
                file_path="test.py",
                symbol_type=SymbolType.CLASS,
                name=f"class_{i}",
                qualified_name=f"class_{i}",
                line_start=i + 10,
                line_end=i + 20,
                content_hash=f"class_hash{i}",
            )
            await symbol_repo.create(symbol)
        
        # Get function symbols
        function_symbols = await symbol_repo.get_by_project(project_id, SymbolType.FUNCTION)
        class_symbols = await symbol_repo.get_by_project(project_id, SymbolType.CLASS)
        
        assert len(function_symbols) == 2
        assert all(s.symbol_type == SymbolType.FUNCTION for s in function_symbols)
        assert len(class_symbols) == 3
        assert all(s.symbol_type == SymbolType.CLASS for s in class_symbols)
    
    @pytest.mark.asyncio
    async def test_search_symbols_by_name(self, symbol_repo: SymbolRepository):
        """Test searching symbols by name pattern."""
        project_id = uuid4()
        
        # Create symbols with different names
        names = ["test_function", "helper_function", "test_class", "another_function"]
        for name in names:
            symbol = Symbol(
                id=uuid4(),
                project_id=project_id,
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=name,
                qualified_name=name,
                line_start=1,
                line_end=5,
                content_hash="hash",
            )
            await symbol_repo.create(symbol)
        
        # Search for symbols containing "test"
        test_symbols = await symbol_repo.search_by_name(project_id, "test")
        
        assert len(test_symbols) == 2
        for symbol in test_symbols:
            assert "test" in symbol.name.lower()
    
    @pytest.mark.asyncio
    async def test_delete_symbols_by_project(self, symbol_repo: SymbolRepository):
        """Test deleting all symbols for a project."""
        project_id = uuid4()
        
        # Create symbols for the project
        for i in range(5):
            symbol = Symbol(
                id=uuid4(),
                project_id=project_id,
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=f"function_{i}",
                qualified_name=f"function_{i}",
                line_start=i + 1,
                line_end=i + 5,
                content_hash=f"hash{i}",
            )
            await symbol_repo.create(symbol)
        
        # Delete symbols for the project
        deleted_count = await symbol_repo.delete_by_project(project_id)
        
        assert deleted_count == 5
        
        # Verify symbols are gone
        remaining_symbols = await symbol_repo.get_by_project(project_id)
        assert len(remaining_symbols) == 0
    
    @pytest.mark.asyncio
    async def test_delete_symbols_by_file(self, symbol_repo: SymbolRepository):
        """Test deleting all symbols in a specific file."""
        project_id = uuid4()
        
        # Create symbols in different files
        files = ["file1.py", "file2.py"]
        for file_path in files:
            for i in range(3):
                symbol = Symbol(
                    id=uuid4(),
                    project_id=project_id,
                    file_path=file_path,
                    symbol_type=SymbolType.FUNCTION,
                    name=f"function_{file_path}_{i}",
                    qualified_name=f"function_{file_path}_{i}",
                    line_start=i + 1,
                    line_end=i + 5,
                    content_hash=f"hash{i}",
                )
                await symbol_repo.create(symbol)
        
        # Delete symbols in file1.py
        deleted_count = await symbol_repo.delete_by_file(project_id, "file1.py")
        
        assert deleted_count == 3
        
        # Verify only file2.py symbols remain
        remaining_symbols = await symbol_repo.get_by_project(project_id)
        assert len(remaining_symbols) == 3
        for symbol in remaining_symbols:
            assert symbol.file_path == "file2.py"
    
    @pytest.mark.asyncio
    async def test_get_symbols_with_todos(self, symbol_repo: SymbolRepository):
        """Test getting symbols that contain TODO comments."""
        project_id = uuid4()
        
        # Create symbols with and without TODOs
        symbols_data = [
            ("function_with_todo", True),
            ("function_without_todo", False),
            ("class_with_todo", True),
        ]
        
        for name, has_todo in symbols_data:
            symbol = Symbol(
                id=uuid4(),
                project_id=project_id,
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=name,
                qualified_name=name,
                line_start=1,
                line_end=5,
                content_hash="hash",
                has_todo=has_todo,
            )
            await symbol_repo.create(symbol)
        
        # Get symbols with TODOs
        todo_symbols = await symbol_repo.get_symbols_with_todos(project_id)
        
        assert len(todo_symbols) == 2
        for symbol in todo_symbols:
            assert symbol.has_todo is True
            assert "todo" in symbol.name.lower()
