"""Tests for API layer (FastAPI routes)."""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

from vault.main import app
from vault.storage.models import Project, Symbol, ProjectType, IndexStatus, SymbolType


class TestHealthEndpoints:
    """Test cases for health check endpoints."""
    
    def test_health_check(self):
        """Test the health check endpoint."""
        with TestClient(app) as client:
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
    
    def test_root_endpoint(self):
        """Test the root endpoint."""
        with TestClient(app) as client:
            response = client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "The Vault API"
            assert data["version"] == "0.1.0"


class TestProjectEndpoints:
    """Test cases for project management endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_projects_empty(self, temp_db):
        """Test listing projects when none exist."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/projects/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["projects"] == []
            assert data["total"] == 0
            assert data["page"] == 1
    
    @pytest.mark.asyncio
    async def test_create_and_get_project(self, temp_db):
        """Test creating and retrieving a project."""
        project_data = {
            "name": "TestProject",
            "path": "/test/project",
            "type": "python",
            "language_primary": "python",
            "loc_total": 100,
            "file_count": 5,
            "health_score": 0.8,
            "index_status": "pending",
            "git_has": False,
        }
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create project (would normally be done via scanning)
            # For testing, we'll insert directly into DB
            from vault.storage.repositories import ProjectRepository
            project_repo = ProjectRepository(temp_db)
            
            project = Project(
                id=uuid4(),
                **project_data
            )
            await project_repo.create(project)
            await temp_db.commit()  # Ensure the project is committed
            
            # Get project via API
            response = await client.get(f"/projects/{project.id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "TestProject"
            assert data["type"] == "python"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_project(self, temp_db):
        """Test getting a non-existent project."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/projects/{uuid4()}")
            
            assert response.status_code == 404
            assert "Project not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_project(self, temp_db):
        """Test updating a project."""
        from vault.storage.repositories import ProjectRepository
        project_repo = ProjectRepository(temp_db)
        
        # Create project
        project = Project(
            id=uuid4(),
            name="TestProject",
            path="/test/project",
            type=ProjectType.PYTHON,
        )
        await project_repo.create(project)
        
        update_data = {
            "name": "UpdatedProject",
            "loc_total": 200,
        }
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/projects/{project.id}",
                json=update_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "UpdatedProject"
            assert data["loc_total"] == 200
    
    @pytest.mark.asyncio
    async def test_delete_project(self, temp_db):
        """Test deleting a project."""
        from vault.storage.repositories import ProjectRepository
        project_repo = ProjectRepository(temp_db)
        
        # Create project
        project = Project(
            id=uuid4(),
            name="TestProject",
            path="/test/project",
            type=ProjectType.PYTHON,
        )
        await project_repo.create(project)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(f"/projects/{project.id}")
            
            assert response.status_code == 200
            assert "deleted successfully" in response.json()["message"]
    
    @pytest.mark.asyncio
    async def test_list_projects_with_filters(self, temp_db):
        """Test listing projects with type and status filters."""
        from vault.storage.repositories import ProjectRepository
        project_repo = ProjectRepository(temp_db)
        
        # Create projects with different types and statuses
        python_project = Project(
            id=uuid4(),
            name="PythonProject",
            path="/test/python",
            type=ProjectType.PYTHON,
            index_status=IndexStatus.COMPLETE,
        )
        java_project = Project(
            id=uuid4(),
            name="JavaProject",
            path="/test/java",
            type=ProjectType.JAVA,
            index_status=IndexStatus.PENDING,
        )
        
        await project_repo.create(python_project)
        await project_repo.create(java_project)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Filter by type
            response = await client.get("/projects/?type=python")
            data = response.json()
            assert len(data["projects"]) == 1
            assert data["projects"][0]["type"] == "python"
            
            # Filter by status
            response = await client.get("/projects/?status=complete")
            data = response.json()
            assert len(data["projects"]) == 1
            assert data["projects"][0]["index_status"] == "complete"

    @pytest.mark.asyncio
    async def test_list_projects_search(self, temp_db):
        """Test searching projects by name."""
        from vault.storage.repositories import ProjectRepository
        project_repo = ProjectRepository(temp_db)
        
        await project_repo.create(Project(id=uuid4(), name="AlphaProject", path="/a", type=ProjectType.PYTHON))
        await project_repo.create(Project(id=uuid4(), name="BetaProject", path="/b", type=ProjectType.PYTHON))
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/projects/?search=alpha")
            data = response.json()
            assert len(data["projects"]) == 1
            assert data["projects"][0]["name"] == "AlphaProject"

    @pytest.mark.asyncio
    async def test_list_projects_pagination(self, temp_db):
        """Test pagination for project listing."""
        from vault.storage.repositories import ProjectRepository
        project_repo = ProjectRepository(temp_db)
        
        for i in range(5):
            await project_repo.create(Project(id=uuid4(), name=f"P{i}", path=f"/{i}", type=ProjectType.PYTHON))
            
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Page 1, size 2
            response = await client.get("/projects/?page=1&page_size=2")
            data = response.json()
            assert len(data["projects"]) == 2
            assert data["total"] == 5
            
            # Page 3, size 2 (should have 1 item)
            response = await client.get("/projects/?page=3&page_size=2")
            data = response.json()
            assert len(data["projects"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_project_statistics(self, temp_db):
        """Test getting project statistics."""
        from vault.storage.repositories import ProjectRepository
        project_repo = ProjectRepository(temp_db)
        
        # Create test projects
        for i in range(3):
            project = Project(
                id=uuid4(),
                name=f"Project{i}",
                path=f"/test/project{i}",
                type=ProjectType.PYTHON if i < 2 else ProjectType.JAVA,
                index_status=IndexStatus.COMPLETE,
                file_count=i + 1,
                loc_total=(i + 1) * 10,
            )
            await project_repo.create(project)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/projects/statistics/overview")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_projects"] == 3
            assert data["by_type"]["python"] == 2
            assert data["by_type"]["java"] == 1
            assert data["total_files"] == 6  # 1 + 2 + 3
            assert data["total_loc"] == 60  # 10 + 20 + 30


class TestSymbolEndpoints:
    """Test cases for symbol management endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_project_symbols_empty(self, temp_db):
        """Test getting symbols for a project with no symbols."""
        from vault.storage.repositories import ProjectRepository, SymbolRepository
        project_repo = ProjectRepository(temp_db)
        
        # Create project
        project = Project(
            id=uuid4(),
            name="TestProject",
            path="/test/project",
            type=ProjectType.PYTHON,
        )
        await project_repo.create(project)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/symbols/project/{project.id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbols"] == []
            assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_get_project_symbols_with_data(self, temp_db):
        """Test getting symbols for a project with symbols."""
        from vault.storage.repositories import ProjectRepository, SymbolRepository
        project_repo = ProjectRepository(temp_db)
        symbol_repo = SymbolRepository(temp_db)
        
        # Create project
        project = Project(
            id=uuid4(),
            name="TestProject",
            path="/test/project",
            type=ProjectType.PYTHON,
        )
        await project_repo.create(project)
        
        # Create symbols
        symbols = []
        for i in range(3):
            symbol = Symbol(
                id=uuid4(),
                project_id=project.id,
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=f"function_{i}",
                qualified_name=f"function_{i}",
                line_start=i + 1,
                line_end=i + 5,
                content_hash=f"hash{i}",
            )
            symbols.append(symbol)
        
        await symbol_repo.create_batch(symbols)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/symbols/project/{project.id}")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["symbols"]) == 3
            assert data["total"] == 3
    
    @pytest.mark.asyncio
    async def test_get_symbols_by_type(self, temp_db):
        """Test getting symbols filtered by type."""
        from vault.storage.repositories import ProjectRepository, SymbolRepository
        project_repo = ProjectRepository(temp_db)
        symbol_repo = SymbolRepository(temp_db)
        
        # Create project
        project = Project(
            id=uuid4(),
            name="TestProject",
            path="/test/project",
            type=ProjectType.PYTHON,
        )
        await project_repo.create(project)
        
        # Create symbols of different types
        class_symbol = Symbol(
            id=uuid4(),
            project_id=project.id,
            file_path="test.py",
            symbol_type=SymbolType.CLASS,
            name="TestClass",
            qualified_name="TestClass",
            line_start=1,
            line_end=10,
            content_hash="class_hash",
        )
        
        function_symbol = Symbol(
            id=uuid4(),
            project_id=project.id,
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="test_function",
            qualified_name="test_function",
            line_start=11,
            line_end=15,
            content_hash="func_hash",
        )
        
        await symbol_repo.create_batch([class_symbol, function_symbol])
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Get only class symbols
            response = await client.get(f"/symbols/project/{project.id}?symbol_type=class")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["symbols"]) == 1
            assert data["symbols"][0]["symbol_type"] == "class"
            assert data["symbols"][0]["name"] == "TestClass"
    
    @pytest.mark.asyncio
    async def test_search_symbols(self, temp_db):
        """Test searching symbols by name."""
        from vault.storage.repositories import ProjectRepository, SymbolRepository
        project_repo = ProjectRepository(temp_db)
        symbol_repo = SymbolRepository(temp_db)
        
        # Create project
        project = Project(
            id=uuid4(),
            name="TestProject",
            path="/test/project",
            type=ProjectType.PYTHON,
        )
        await project_repo.create(project)
        
        # Create symbols with different names
        symbols = []
        names = ["test_function", "helper_function", "test_class"]
        for name in names:
            symbol = Symbol(
                id=uuid4(),
                project_id=project.id,
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=name,
                qualified_name=name,
                line_start=1,
                line_end=5,
                content_hash="hash",
            )
            symbols.append(symbol)
        
        await symbol_repo.create_batch(symbols)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Search for symbols containing "test"
            response = await client.get(f"/symbols/project/{project.id}/search?query=test")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            
            symbol_names = {s["name"] for s in data}
            assert "test_function" in symbol_names
            assert "test_class" in symbol_names
    
    @pytest.mark.asyncio
    async def test_get_symbols_with_todos(self, temp_db):
        """Test getting symbols that contain TODO comments."""
        from vault.storage.repositories import ProjectRepository, SymbolRepository
        project_repo = ProjectRepository(temp_db)
        symbol_repo = SymbolRepository(temp_db)
        
        # Create project
        project = Project(
            id=uuid4(),
            name="TestProject",
            path="/test/project",
            type=ProjectType.PYTHON,
        )
        await project_repo.create(project)
        
        # Create symbols with and without TODOs
        todo_symbol = Symbol(
            id=uuid4(),
            project_id=project.id,
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="function_with_todo",
            qualified_name="function_with_todo",
            line_start=1,
            line_end=5,
            content_hash="hash",
            has_todo=True,
        )
        
        normal_symbol = Symbol(
            id=uuid4(),
            project_id=project.id,
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="normal_function",
            qualified_name="normal_function",
            line_start=6,
            line_end=10,
            content_hash="hash2",
            has_todo=False,
        )
        
        await symbol_repo.create_batch([todo_symbol, normal_symbol])
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/symbols/project/{project.id}/todos")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "function_with_todo"
            assert data[0]["has_todo"] is True

    @pytest.mark.asyncio
    async def test_get_symbol_stats_per_project(self, temp_db):
        """Test getting symbol statistics for a project."""
        from vault.storage.repositories import ProjectRepository, SymbolRepository
        project_repo = ProjectRepository(temp_db)
        symbol_repo = SymbolRepository(temp_db)
        
        project = Project(id=uuid4(), name="P", path="/p", type=ProjectType.PYTHON)
        await project_repo.create(project)
        
        s1 = Symbol(id=uuid4(), project_id=project.id, file_path="f1.py", symbol_type=SymbolType.CLASS, name="C", qualified_name="C", line_start=1, line_end=5, content_hash="h1")
        s2 = Symbol(id=uuid4(), project_id=project.id, file_path="f1.py", symbol_type=SymbolType.FUNCTION, name="F", qualified_name="F", line_start=6, line_end=10, content_hash="h2")
        await symbol_repo.create_batch([s1, s2])
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/symbols/project/{project.id}/statistics")
            data = response.json()
            assert data["total_symbols"] == 2
            assert data["symbol_counts"]["class"] == 1

    @pytest.mark.asyncio
    async def test_get_symbols_by_file(self, temp_db):
        """Test getting symbols from a specific file."""
        from vault.storage.repositories import ProjectRepository, SymbolRepository
        project_repo = ProjectRepository(temp_db)
        symbol_repo = SymbolRepository(temp_db)
        
        project = Project(id=uuid4(), name="P", path="/p", type=ProjectType.PYTHON)
        await project_repo.create(project)
        
        s1 = Symbol(id=uuid4(), project_id=project.id, file_path="target.py", symbol_type=SymbolType.CLASS, name="C", qualified_name="C", line_start=1, line_end=5, content_hash="h1")
        s2 = Symbol(id=uuid4(), project_id=project.id, file_path="other.py", symbol_type=SymbolType.CLASS, name="O", qualified_name="O", line_start=1, line_end=5, content_hash="h2")
        await symbol_repo.create_batch([s1, s2])
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/symbols/project/{project.id}/file/target.py")
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "C"


class TestIndexerEndpoints:
    """Test cases for indexing and parsing endpoints."""
    
    @pytest.mark.asyncio
    async def test_start_parsing_project(self, temp_db):
        """Test starting parsing for a project."""
        from vault.storage.repositories import ProjectRepository
        project_repo = ProjectRepository(temp_db)
        
        # Create project
        project = Project(
            id=uuid4(),
            name="TestProject",
            path="/test/project",
            type=ProjectType.PYTHON,
        )
        await project_repo.create(project)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/indexer/projects/{project.id}/parse")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["project_id"] == str(project.id)
    
    @pytest.mark.asyncio
    async def test_get_parsing_status(self, temp_db):
        """Test getting parsing status for a project."""
        from vault.storage.repositories import ProjectRepository
        project_repo = ProjectRepository(temp_db)
        
        # Create project
        project = Project(
            id=uuid4(),
            name="TestProject",
            path="/test/project",
            type=ProjectType.PYTHON,
            index_status=IndexStatus.PENDING,
        )
        await project_repo.create(project)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/indexer/projects/{project.id}/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["project_id"] == str(project.id)
            assert data["status"] == "pending"
            assert data["is_parsing"] is False
    
    @pytest.mark.asyncio
    async def test_get_active_parsing_tasks(self, temp_db):
        """Test getting list of active parsing tasks."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/indexer/status/active")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_indexing_overview(self, temp_db):
        """Test getting indexing overview across all projects."""
        from vault.storage.repositories import ProjectRepository
        project_repo = ProjectRepository(temp_db)
        
        # Create test projects with different statuses
        for i, status in enumerate([IndexStatus.PENDING, IndexStatus.COMPLETE, IndexStatus.ERROR]):
            project = Project(
                id=uuid4(),
                name=f"Project{i}",
                path=f"/test/project{i}",
                type=ProjectType.PYTHON,
                index_status=status,
            )
            await project_repo.create(project)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/indexer/status/overview")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_projects"] == 3
            assert data["status_counts"]["pending"] == 1
            assert data["status_counts"]["complete"] == 1
            assert data["status_counts"]["error"] == 1
            assert "timestamp" in data


class TestErrorHandling:
    """Test cases for API error handling."""
    
    @pytest.mark.asyncio
    async def test_invalid_project_id(self, temp_db):
        """Test handling of invalid project ID."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/projects/invalid-uuid")
            
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_invalid_symbol_type_filter(self, temp_db):
        """Test handling of invalid symbol type filter."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/symbols/project/{uuid4()}?symbol_type=invalid")
            
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_missing_request_body(self, temp_db):
        """Test handling of missing request body."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/indexer/projects/batch-parse")
            
            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_scan_projects(self, temp_db, temp_project_dir):
        """Test scanning for projects."""
        # Create a dummy project structure
        py_project = temp_project_dir / "my_py_project"
        py_project.mkdir()
        (py_project / "requirements.txt").write_text("")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Scan specific directory
            payload = {"root_directories": [str(temp_project_dir)]}
            response = await client.post("/projects/scan", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["discovered_count"] >= 1

    @pytest.mark.asyncio
    async def test_batch_parse_projects(self, temp_db):
        """Test batch parsing via API."""
        from vault.storage.repositories import ProjectRepository
        project_repo = ProjectRepository(temp_db)
        p1 = Project(id=uuid4(), name="P1", path="/p1", type=ProjectType.PYTHON)
        p2 = Project(id=uuid4(), name="P2", path="/p2", type=ProjectType.PYTHON)
        await project_repo.create(p1)
        await project_repo.create(p2)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {"project_ids": [str(p1.id), str(p2.id)]}
            response = await client.post("/indexer/projects/batch-parse", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["projects_attempted"] == 2
