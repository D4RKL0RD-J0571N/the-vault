"""Tests to close coverage gaps in API, Main and Parser modules."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4
from fastapi import HTTPException
from vault.exceptions import VaultError, ParsingError
from vault.storage.models import IndexStatus, ProjectType
from vault.api.indexer import (
    parse_multiple_projects, 
    get_parsing_status, 
    get_active_parsing_tasks,
    get_indexing_overview,
    reparse_file
)
from vault.storage.repositories import ProjectRepository, SymbolRepository
from vault.api.projects import (
    list_projects,
    get_project,
    scan_projects,
    update_project,
    delete_project,
    refresh_project,
    get_project_statistics
)
from vault.api.schemas import ParseRequest, ScanRequest, ProjectUpdate
from vault.parser import ParsingService, TreeSitterParser

@pytest.mark.asyncio
async def test_indexer_api_gaps():
    service = MagicMock(spec=ParsingService)
    
    # 1. parse_multiple_projects: No project IDs (Line 73)
    request = ParseRequest(project_ids=[])
    with pytest.raises(HTTPException) as exc:
        await parse_multiple_projects(request, service)
    assert exc.value.status_code == 400
    
    # 2. parse_multiple_projects: General Exception (Line 87)
    request = ParseRequest(project_ids=[uuid4()])
    service.parse_multiple_projects = AsyncMock(side_effect=Exception("Batch fail"))
    res = await parse_multiple_projects(request, service)
    assert res.success is False
    assert "Batch fail" in res.message

    # 3. get_parsing_status: Not found (Line 104)
    service.get_parsing_status = AsyncMock(return_value={"success": False, "error": "Not found"})
    with pytest.raises(HTTPException) as exc:
        await get_parsing_status(uuid4(), service)
    assert exc.value.status_code == 404

    # 4. get_parsing_status: General Exception (Line 118)
    service.get_parsing_status = AsyncMock(side_effect=Exception("Status fail"))
    with pytest.raises(HTTPException) as exc:
        await get_parsing_status(uuid4(), service)
    assert exc.value.status_code == 500

    # 5. get_active_parsing_tasks: Exception (Line 154)
    service.get_active_parsing_tasks = AsyncMock(side_effect=Exception("Active fail"))
    with pytest.raises(HTTPException) as exc:
        await get_active_parsing_tasks(service)
    assert exc.value.status_code == 500

    # 6. get_indexing_overview: Exception (Line 181)
    repo = MagicMock()
    repo.get_all = AsyncMock(side_effect=Exception("Overview fail"))
    with pytest.raises(HTTPException) as exc:
        await get_indexing_overview(repo)
    assert exc.value.status_code == 500

    # 7. reparse_file: Exception (Line 197)
    service.parser = MagicMock()
    service.parser.reparse_changed_file = AsyncMock(side_effect=Exception("Reparse fail"))
    res = await reparse_file(uuid4(), "file.py", service)
    assert res["success"] is False
    assert "Reparse fail" in res["error"]

@pytest.mark.asyncio
async def test_projects_api_gaps():
    repo = MagicMock()
    
    # 1. list_projects: Exception (Line 80)
    repo.get_all = AsyncMock(side_effect=Exception("List fail"))
    with pytest.raises(HTTPException) as exc:
        await list_projects(project_repo=repo)
    assert exc.value.status_code == 500

    # 2. get_project: Not found (Line 101/92)
    repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as exc:
        await get_project(uuid4(), repo)
    assert exc.value.status_code == 404

    # 3. scan_projects: Root dirs scan success (Line 119)
    service = MagicMock()
    service.scan_specific_path = AsyncMock(return_value={"success": True, "projects": [], "discovered_count": 0})
    request = ScanRequest(root_directories=["/test"])
    res = await scan_projects(request, service)
    assert res.success is True

    # 4. scan_projects: Exception (Line 138)
    service.discover_all_projects = AsyncMock(side_effect=Exception("Scan fail"))
    request = ScanRequest(root_directories=[])
    res = await scan_projects(request, service)
    assert res.success is False
    assert "Scan fail" in res.error

    # 5. update_project: Empty data (Line 159)
    update_req = ProjectUpdate() # Empty
    with pytest.raises(HTTPException) as exc:
        await update_project(uuid4(), update_req, repo)
    assert exc.value.status_code == 400

    # 6. update_project: Exception (Line 169)
    update_req = ProjectUpdate(name="New")
    repo.update = AsyncMock(side_effect=Exception("Update fail"))
    with pytest.raises(HTTPException) as exc:
        await update_project(uuid4(), update_req, repo)
    assert exc.value.status_code == 500

    # 7. delete_project: Not success (Line 181)
    repo.delete = AsyncMock(return_value=False)
    with pytest.raises(HTTPException) as exc:
        await delete_project(uuid4(), repo)
    assert exc.value.status_code == 404

    # 8. delete_project: Exception (Line 189)
    repo.delete = AsyncMock(side_effect=Exception("Delete fail"))
    with pytest.raises(HTTPException) as exc:
        await delete_project(uuid4(), repo)
    assert exc.value.status_code == 500

    # 9. refresh_project: Status 501 (Line 216)
    with pytest.raises(HTTPException) as exc:
        await refresh_project(uuid4(), MagicMock())
    assert exc.value.status_code == 501

    # 10. refresh_project: Exception (Line 223)
    # This might be tricky because refresh_project raises 501 immediately.
    # To hit 223, it must raise something else before 216? No, the code is:
    # try: raise 501 except HTTPException: raise except Exception: raise 500
    # But wait, if I mock something... actually refresh_project doesn't use any dependency before raising 501.
    # Oh, discovery_service is a dependency. If it fails...
    # But it's passed as an argument.
    
    # 11. get_project_statistics: Exception (Line 203)
    service.get_project_statistics = AsyncMock(side_effect=Exception("Stats fail"))
    with pytest.raises(HTTPException) as exc:
        await get_project_statistics(service)
    assert exc.value.status_code == 500

@pytest.mark.asyncio
async def test_main_exception_handlers():
    from vault.main import vault_exception_handler, http_exception_handler, general_exception_handler
    request = MagicMock()
    request.url.path = "/test"
    
    # vault_exception_handler
    exc = VaultError("Vault error", {"d": 1})
    res = await vault_exception_handler(request, exc)
    assert res.status_code == 500
    
    # http_exception_handler
    exc_h = HTTPException(status_code=403, detail="Forbidden")
    res = await http_exception_handler(request, exc_h)
    assert res.status_code == 403
    
    # general_exception_handler
    exc_g = Exception("Boom")
    res = await general_exception_handler(request, exc_g)
    assert res.status_code == 500

@pytest.mark.asyncio
async def test_tree_sitter_parser_gaps():
    project_repo = MagicMock(spec=ProjectRepository)
    symbol_repo = MagicMock(spec=SymbolRepository)
    # Ensure methods are AsyncMock
    project_repo.get_by_id = AsyncMock()
    project_repo.update_status = AsyncMock()
    symbol_repo.delete_by_project = AsyncMock()
    symbol_repo.delete_by_file = AsyncMock()
    symbol_repo.get_by_project = AsyncMock()
    symbol_repo.create_batch = AsyncMock()
    
    parser = TreeSitterParser(project_repo, symbol_repo)
    
    p_id = uuid4()
    
    # 1. parse_project: Not found (Line 28)
    project_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="not found"):
        await parser.parse_project(p_id)
        
    # 2. parse_project: General Exception (Line 66)
    project_repo.get_by_id = AsyncMock(return_value=MagicMock())
    # Mock update_status to fail only on first call or similar
    # Actually, if we want to hit line 66, we just need something to fail inside the try block
    # AFTER the first update_status(PARSING).
    project_repo.update_status = AsyncMock()
    with patch.object(parser, "_get_project_files", AsyncMock(side_effect=Exception("Failed status"))):
        res = await parser.parse_project(p_id)
        assert res["success"] is False
        assert "Failed status" in res["error"]

    # 3. parse_file: Not found (Line 83)
    project_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="not found"):
        await parser.parse_file(p_id, "file.py")

    # 4. reparse_changed_file: Not found (Line 92)
    project_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="not found"):
        await parser.reparse_changed_file(p_id, "file.py")

    # 5. reparse_changed_file: Exception (Line 112)
    project_repo.get_by_id = AsyncMock(return_value=MagicMock(path="/p"))
    symbol_repo.delete_by_file = AsyncMock(side_effect=Exception("Delete fail"))
    res = await parser.reparse_changed_file(p_id, "file.py")
    assert res["success"] is False
    assert "Delete fail" in res["error"]

    # 6. _should_include_file: OSError (Line 201-203)
    mock_file = MagicMock()
    mock_file.stat.side_effect = OSError()
    with patch.object(parser.fingerprinter, "_get_language_by_extension", return_value="python"):
        assert parser._should_include_file(mock_file) is False

    # 7. ParsingService: Already parsing (Line 220)
    service = ParsingService(project_repo, symbol_repo)
    service._active_tasks[p_id] = MagicMock()
    res = await service.start_parsing_project(p_id)
    assert res["success"] is False
    assert "already" in res["message"]

    # 8. ParsingService: Not found (Line 229)
    service._active_tasks = {}
    project_repo.get_by_id = AsyncMock(return_value=None)
    res = await service.start_parsing_project(p_id)
    assert res["success"] is False
    assert "not found" in res["message"]

    # 9. ParsingService: No active task to cancel (Line 268)
    res = await service.cancel_parsing(p_id)
    assert res["success"] is False

    # 10. ParsingService: CancelledError (Line 279)
    mock_task = asyncio.create_task(asyncio.sleep(0.1))
    service._active_tasks[p_id] = mock_task
    task_res = await service.cancel_parsing(p_id)
    assert task_res["success"] is True

@pytest.mark.asyncio
async def test_parse_multiple_projects_failures():
    project_repo = MagicMock()
    symbol_repo = MagicMock()
    service = ParsingService(project_repo, symbol_repo)
    
    p_id = uuid4()
    # Mock parse_project to return failure
    service.parser.parse_project = AsyncMock(return_value={"success": False})
    
    res = await service.parse_multiple_projects([p_id])
    assert res["failed"] == 1
    
    # Mock parse_project to raise exception
    service.parser.parse_project = AsyncMock(side_effect=Exception("Fail"))
    res = await service.parse_multiple_projects([p_id])
    assert res["failed"] == 1

@pytest.mark.asyncio
async def test_symbol_extractor_base_gaps():
    from vault.parser.extractors import SymbolExtractor
    with patch.object(SymbolExtractor, "_setup_parser"):
        ext = SymbolExtractor("python")
        # 1. _extract_from_node base (Line 81)
        assert ext._extract_from_node(MagicMock(), "", Path("f.py"), "pid", []) is None
        # 2. _get_symbol_name base (Line 105)
        assert ext._get_symbol_name(MagicMock(), "") is None

@pytest.mark.asyncio
async def test_main_cli_gaps():
    from vault.main import cli, run_scan_command, run_serve_command
    
    # 1. cli print_help (Line 226)
    with patch("argparse.ArgumentParser.parse_args") as mock_args:
        mock_args.return_value = MagicMock(command=None)
        with patch("argparse.ArgumentParser.print_help") as mock_print:
            await cli()
            mock_print.assert_called_once()
            
    # 2. run_scan_command: Root dirs scan success (Line 268-273)
    mock_args = MagicMock(command="scan", directories=[], output="table")
    with patch("vault.crawler.ProjectDiscoveryService") as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.discover_all_projects = AsyncMock(return_value={
            "success": True, 
            "discovered_count": 1, 
            "projects": [MagicMock(name="P", type=MagicMock(value="python"), file_count=1, loc_total=1, languages={})]
        })
        with patch("vault.storage.get_db_session") as mock_db:
            mock_db.return_value.__aenter__.return_value = MagicMock()
            with patch("builtins.print") as mock_print:
                await run_scan_command(mock_args)
                # Confirm it printed something
                assert mock_print.called

    # 3. run_scan_command: Scan specific dirs with error (Line 249)
    mock_args = MagicMock(command="scan", directories=["/err"], output="json")
    with patch("vault.crawler.ProjectDiscoveryService") as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.scan_specific_path = AsyncMock(return_value={
            "success": False, "error": "Disk full", "discovered_count": 0
        })
        with patch("vault.storage.get_db_session") as mock_db:
            mock_db.return_value.__aenter__.return_value = MagicMock()
            with patch("builtins.print") as mock_print:
                await run_scan_command(mock_args)
                # Should print error
                mock_print.assert_any_call("Error scanning /err: Disk full")

    # 4. run_serve_command (Line 276-291)
    mock_args = MagicMock(host="127.0.0.1", port=8000)
    with patch("uvicorn.Server.serve", new_callable=AsyncMock) as mock_serve:
        await run_serve_command(mock_args)
        mock_serve.assert_called_once()

@pytest.mark.asyncio
async def test_tree_sitter_parsing_error_loop():
    project_repo = MagicMock(spec=ProjectRepository)
    symbol_repo = MagicMock(spec=SymbolRepository)
    project_repo.get_by_id = AsyncMock()
    project_repo.update_status = AsyncMock()
    symbol_repo.delete_by_project = AsyncMock()
    symbol_repo.create_batch = AsyncMock()
    
    parser = TreeSitterParser(project_repo, symbol_repo)
    
    p_id = uuid4()
    project_repo.get_by_id = AsyncMock(return_value=MagicMock(path="/p", id=p_id))
    # Mock _get_project_files to return one file
    with patch.object(parser, "_get_project_files", AsyncMock(return_value=[Path("/p/f.py")])):
        # Mock _parse_file to raise ParsingError (Line 46-49)
        with patch.object(parser, "_parse_file", AsyncMock(side_effect=ParsingError("Parse fail"))):
            with patch("builtins.print") as mock_print:
                res = await parser.parse_project(p_id)
                assert res["success"] is True
                # The path in print message depends on OS, but should contain f.py
                found = False
                for call in mock_print.call_args_list:
                    if "f.py" in str(call) and "Parse fail" in str(call):
                        found = True
                assert found

@pytest.mark.asyncio
async def test_tree_sitter_helpers():
    project_repo = MagicMock()
    symbol_repo = MagicMock()
    parser = TreeSitterParser(project_repo, symbol_repo)
    
    # 1. _should_exclude_directory: starts with . (Line 189)
    assert parser._should_exclude_directory(Path(".git")) is True
    
    # 2. _should_include_file: no language (Line 196)
    with patch.object(parser.fingerprinter, "_get_language_by_extension", return_value=None):
        assert parser._should_include_file(Path("data.txt")) is False
        
    # 3. _parse_file: no language (Line 171)
    with patch.object(parser.fingerprinter, "_get_language_by_extension", return_value=None):
        assert await parser._parse_file(Path("data.txt"), uuid4()) == []

@pytest.mark.asyncio
async def test_main_cli_json_output():
    from vault.main import run_scan_command
    mock_args = MagicMock(command="scan", directories=["/p"], output="json")
    with patch("vault.crawler.ProjectDiscoveryService") as mock_service_cls:
        mock_service = mock_service_cls.return_value
        p = MagicMock()
        p.name = "P"
        p.path = "/p"
        p.file_count = 1
        p.loc_total = 1
        p.type.value = "python"
        mock_service.scan_specific_path = AsyncMock(return_value={
            "success": True, "projects": [p], "discovered_count": 1
        })
        with patch("vault.storage.get_db_session") as mock_db:
            mock_db.return_value.__aenter__.return_value = MagicMock()
            with patch("builtins.print") as mock_print:
                await run_scan_command(mock_args)
                # Should print JSON
                json_printed = False
                for call in mock_print.call_args_list:
                    if '"name": "P"' in str(call):
                        json_printed = True
                assert json_printed
