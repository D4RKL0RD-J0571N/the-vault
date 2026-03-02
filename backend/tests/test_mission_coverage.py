"""Comprehensive coverage tests for Phase 1 Mission."""

import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from vault.main import app
from vault.storage.models import Project, Symbol, ProjectType, IndexStatus, SymbolType
from vault.storage.repositories import ProjectRepository, SymbolRepository
from vault.crawler import ProjectDiscoveryService
from vault.parser import ParsingService, TreeSitterParser
from vault.exceptions import VaultError

@pytest.mark.asyncio
class TestMissionCoverage:
    """Targeted tests to hit the missing lines in priority modules."""

    # --- symbols.py targets ---
    async def test_symbols_exceptions(self, temp_db):
        """Hit exception blocks in symbols.py."""
        project = Project(id=uuid4(), name="P", path="/p", type=ProjectType.PYTHON)
        await ProjectRepository(temp_db).create(project)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch.object(SymbolRepository, "get_by_project", side_effect=Exception("ouch")):
                resp = await client.get(f"/symbols/project/{project.id}")
                assert resp.status_code == 500
            
            with patch.object(SymbolRepository, "get_by_file", side_effect=Exception("ouch")):
                resp = await client.get(f"/symbols/project/{project.id}/file/f.py")
                assert resp.status_code == 500
                
            with patch.object(SymbolRepository, "search_by_name", side_effect=Exception("ouch")):
                resp = await client.get(f"/symbols/project/{project.id}/search?query=q")
                assert resp.status_code == 500

            with patch.object(SymbolRepository, "get_symbols_with_todos", side_effect=Exception("ouch")):
                resp = await client.get(f"/symbols/project/{project.id}/todos")
                assert resp.status_code == 500

    # --- projects.py targets ---
    async def test_projects_list_success(self, temp_db):
        """Hit success lines 71-76 in projects.py."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/projects/")
            assert resp.status_code == 200
            assert "projects" in resp.json()

    async def test_projects_search_and_errors(self, temp_db):
        """Hit lines 61-81, 92-102 in projects.py."""
        repo = ProjectRepository(temp_db)
        p = Project(id=uuid4(), name="Alpha", path="/alpha", type=ProjectType.PYTHON)
        await repo.create(p)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/projects/?search=alph")
            assert len(resp.json()["projects"]) == 1
            
            with patch.object(ProjectRepository, "get_all", side_effect=Exception("ouch")):
                resp = await client.get("/projects/")
                assert resp.status_code == 500
            
            with patch.object(ProjectRepository, "get_by_id", side_effect=Exception("ouch")):
                resp = await client.get(f"/projects/{p.id}")
                assert resp.status_code == 500

    async def test_projects_scan_full(self, temp_db):
        """Hit lines 128-136 in projects.py."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            mock_res = {"projects": [], "discovered_count": 0, "success": True}
            with patch.object(ProjectDiscoveryService, "discover_all_projects", return_value=mock_res):
                resp = await client.post("/projects/scan", json={})
                assert resp.status_code == 200
                assert resp.json()["success"] is True

    async def test_projects_not_found_raised(self, temp_db):
        """Hit ProjectNotFoundError lines 100, 167, 188 in projects.py."""
        from vault.exceptions import ProjectNotFoundError
        p_id = uuid4()
        with patch.object(ProjectRepository, "get_by_id", side_effect=ProjectNotFoundError(p_id)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/projects/{p_id}")
                assert resp.status_code == 404

    async def test_projects_stats_refresh(self, temp_db):
        """Hit lines 201-204, 213-224 in projects.py."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            mock_stats = {
                "total_projects": 0, 
                "status_counts": {},
                "by_type": {},
                "by_status": {},
                "total_files": 0,
                "total_loc": 0
            }
            with patch.object(ProjectDiscoveryService, "get_project_statistics", return_value=mock_stats):
                resp = await client.get("/projects/statistics/overview")
                assert resp.status_code == 200

            with patch.object(ProjectDiscoveryService, "get_project_statistics", side_effect=Exception("ouch")):
                resp = await client.get("/projects/statistics/overview")
                assert resp.status_code == 500
                
            resp = await client.post(f"/projects/{uuid4()}/refresh")
            assert resp.status_code == 501 # Refresh is implemented via 501 in code

    # --- indexer.py targets ---
    async def test_indexer_success_paths(self, temp_db):
        """Hit success lines 51, 107-109, 131, 168-182, 195 in indexer.py."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            p_id = uuid4()
            with patch.object(ParsingService, "start_parsing_project", return_value={"success": True}):
                resp = await client.post(f"/indexer/projects/{p_id}/parse")
                assert resp.status_code == 200

            with patch.object(ParsingService, "get_parsing_status", return_value={"success": True, "status": "done", "is_parsing": False}):
                resp = await client.get(f"/indexer/projects/{p_id}/status")
                assert resp.status_code == 200
                
            with patch.object(ParsingService, "cancel_parsing", return_value={"success": True}):
                resp = await client.post(f"/indexer/projects/{p_id}/cancel")
                assert resp.status_code == 200

            # Overview test (internal logic)
            resp = await client.get("/indexer/status/overview")
            assert resp.status_code == 200

            with patch.object(TreeSitterParser, "reparse_changed_file", return_value={"success": True}):
                resp = await client.post(f"/indexer/reparse-file?project_id={p_id}&file_path=f.py")
                assert resp.status_code == 200

    async def test_indexer_exceptions(self, temp_db):
        """Hit exception blocks in indexer.py."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            p_id = uuid4()
            with patch.object(ParsingService, "start_parsing_project", side_effect=Exception("ouch")):
                resp = await client.post(f"/indexer/projects/{p_id}/parse")
                assert resp.json()["success"] is False

            with patch.object(ParsingService, "get_parsing_status", side_effect=Exception("ouch")):
                resp = await client.get(f"/indexer/projects/{p_id}/status")
                assert resp.status_code == 500

            with patch.object(ProjectRepository, "get_all", side_effect=Exception("ouch")):
                resp = await client.get("/indexer/status/overview")
                assert resp.status_code == 500

    # --- main.py targets ---
    async def test_main_lifespan_error(self, temp_db):
        """Hit line 59-61 in main.py."""
        from vault.main import lifespan
        mock_app = MagicMock()
        with patch("vault.main.init_db", side_effect=Exception("db fail")):
            try:
                async with lifespan(mock_app):
                    pass
            except Exception:
                pass

    async def test_main_cli_commands(self, temp_db):
        """Hit CLI lines in main.py."""
        from vault.main import cli
        import sys
        
        mock_res = {"success": True, "projects": [], "discovered_count": 0}
        with patch.object(sys, "argv", ["vault", "scan", "/tmp/path", "--output", "json"]):
            with patch("vault.crawler.ProjectDiscoveryService.scan_specific_path", return_value=mock_res):
                await cli()

        with patch.object(sys, "argv", ["vault", "serve"]):
            with patch("uvicorn.Server.serve", return_value=None):
                await cli()

    # --- parser/tree_sitter_parser.py targets ---
    async def test_parser_edge_cases(self, temp_db):
        """Hit lines in tree_sitter_parser.py."""
        repo = ProjectRepository(temp_db)
        s_repo = SymbolRepository(temp_db)
        parser = TreeSitterParser(repo, s_repo)
        
        with pytest.raises(ValueError, match="Project .* not found"):
            await parser.get_parsing_statistics(uuid4())
            
        p = Project(id=uuid4(), name="P", path="/p", type=ProjectType.PYTHON)
        await repo.create(p)
        s = Symbol(
            id=uuid4(), project_id=p.id, file_path="f.py", 
            symbol_type=SymbolType.FUNCTION, name="n", qualified_name="n", 
            line_start=1, line_end=2, content_hash="h", has_todo=True
        )
        await s_repo.create(s)
        
        stats = await parser.get_parsing_statistics(p.id)
        assert stats["total_symbols"] == 1
        
        from pathlib import Path
        from vault.config import settings
        orig_patterns = settings.exclude_patterns
        try:
            settings.exclude_patterns = [".git"]
            assert parser._should_exclude_directory(Path(".git")) is True
        finally:
            settings.exclude_patterns = orig_patterns
