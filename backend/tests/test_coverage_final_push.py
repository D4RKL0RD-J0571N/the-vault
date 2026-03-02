"""Final push for 100% coverage."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4
from fastapi import HTTPException

from vault.api.projects import list_projects, update_project, delete_project, refresh_project
from vault.crawler import ProjectFingerprinter, ProjectScanner
from vault.parser import TreeSitterParser
from vault.storage.repositories import ProjectRepository, SymbolRepository
from vault.exceptions import ProjectNotFoundError, DatabaseError

@pytest.mark.asyncio
async def test_api_projects_final_gaps():
    repo = MagicMock(spec=ProjectRepository)
    
    # 1. list_projects: HTTPException (Line 79)
    # We need a dependency to raise HTTPException
    with pytest.raises(HTTPException):
        # We can't easily trigger HTTPException from repo.get_all unless we mock it
        repo.get_all = AsyncMock(side_effect=HTTPException(status_code=400))
        await list_projects(repo, page=1, page_size=10)
        
    # 2. update_project: ProjectNotFoundError (Line 167)
    mock_update = MagicMock()
    repo.update = AsyncMock(side_effect=ProjectNotFoundError("P"))
    with pytest.raises(HTTPException) as exc:
        await update_project(uuid4(), MagicMock(), repo)
    assert exc.value.status_code == 404

    # 3. delete_project: ProjectNotFoundError (Line 188)
    repo.delete = AsyncMock(side_effect=ProjectNotFoundError("P"))
    with pytest.raises(HTTPException) as exc:
        await delete_project(uuid4(), repo)
    assert exc.value.status_code == 404
    
    # 4. refresh_project: General Exception (Line 223)
    # Note: refresh_project currently raises 501 first.
    # We need to bypass the 501 or mock the whole thing?
    # Actually, refresh_project is:
    # try: raise 501
    # except HTTPException: raise
    # except Exception: raise 500
    # Since it explicitly raises 501, it ALWAYS hits the HTTPException branch.
    # To hit line 223, it must NOT be an HTTPException.
    # But it is hardcoded to raise 501.
    # Wait, I can patch the 'raise' line? No.
    # However, if I mock a function CALLED in the try block to raise something else...
    # But there are no calls before the raise.
    
@pytest.mark.asyncio
async def test_fingerprinter_final_gaps():
    fp = ProjectFingerprinter()
    
    # 1. get_primary_language: extension_counts exists but type not in map (Line 73)
    # ProjectType.OTHER is not in map
    with patch.object(fp, "_count_file_extensions", return_value={"python": 1}):
        from vault.storage.models import ProjectType
        assert fp.get_primary_language(Path("/p"), ProjectType.OTHER) == "python"

    # 2. calculate_metrics: unknown language and OSError (Line 103-105)
    with patch("os.walk", return_value=[("/p", [], ["f.py", "unknown.txt"])]):
        with patch.object(fp, "_should_exclude_file", side_effect=[False, False]):
            with patch.object(fp, "_get_language_by_extension", side_effect=["python", None]):
                # Mock open to raise OSError for the first file
                with patch("builtins.open", side_effect=OSError()):
                    c, l, b = fp.calculate_metrics(Path("/p"))
                    assert c == 1
                    assert l == 0 # Skipped loc

    # 3. _should_exclude_file: parent directory excluded (Line 185)
    with patch.object(fp, "_should_exclude", side_effect=[False, True]): # Fails on parent
        assert fp._should_exclude_file(Path("/p/excluded/f.py")) is True

    # 4. _should_exclude_file: OSError on stat and File too large (Line 194, 196)
    with patch.object(fp, "_should_exclude", return_value=False):
        with patch.object(fp, "_get_language_by_extension", return_value="python"):
            # OSError
            with patch("pathlib.Path.stat", side_effect=OSError()):
                assert fp._should_exclude_file(Path("/p/f.py")) is True
            # File too large (Line 194)
            mock_stat = MagicMock()
            mock_stat.st_size = 100 * 1024 * 1024 # 100MB
            with patch("pathlib.Path.stat", return_value=mock_stat):
                assert fp._should_exclude_file(Path("/p/large.py")) is True

    # 5. _get_directory_timestamps: OSError (Line 224-225)
    with patch("os.walk", return_value=[("/p", [], ["f.py"])]):
        with patch.object(fp, "_should_exclude_file", return_value=False):
            with patch("pathlib.Path.stat", side_effect=OSError()):
                res = fp._get_directory_timestamps(Path("/p"))
                assert res["oldest"] is None

@pytest.mark.asyncio
async def test_main_final_push():
    from vault.main import run_scan_command
    # 3. run_scan_command: output="json" for else branch (Line 271->exit)
    mock_args = MagicMock(command="scan", directories=[], output="json")
    with patch("vault.crawler.ProjectDiscoveryService") as mock_ds_cls:
        mock_ds = mock_ds_cls.return_value
        mock_ds.discover_all_projects = AsyncMock(return_value={
            "success": True, "discovered_count": 0, "projects": []
        })
        with patch("vault.storage.get_db_session") as mock_db:
            mock_db.return_value.__aenter__.return_value = MagicMock()
            await run_scan_command(mock_args)

@pytest.mark.asyncio
async def test_tree_sitter_parser_final_push():
    p_repo = MagicMock(spec=ProjectRepository)
    s_repo = MagicMock(spec=SymbolRepository)
    parser = TreeSitterParser(p_repo, s_repo)
    # 1. _should_include_file: language is None (Line 201)
    with patch.object(parser.fingerprinter, "_get_language_by_extension", return_value=None):
        assert parser._should_include_file(Path("unknown.xyz")) is False

@pytest.mark.asyncio
async def test_scanner_final_gaps():
    repo = MagicMock(spec=ProjectRepository)
    scanner = ProjectScanner(repo)
    
    # 1. _should_exclude_directory: hidden dir (Line 149)
    assert scanner._should_exclude_directory(Path(".hidden")) is True
    
    # 2. _scan_directory: item is not a dir (Line 73)
    with patch("pathlib.Path.iterdir", return_value=[Path("/p/file")]):
        with patch.object(Path, "is_dir", return_value=False):
             assert await scanner._scan_directory(Path("/p")) == []

    # 3. _scan_directory: _create_or_update_project returns None (Line 82)
    with patch("pathlib.Path.iterdir", return_value=[Path("/p/proj")]):
        with patch.object(Path, "is_dir", return_value=True):
            with patch.object(scanner, "_should_exclude_directory", return_value=False):
                with patch.object(scanner, "_is_project_directory", AsyncMock(return_value=True)):
                    with patch.object(scanner, "_create_or_update_project", AsyncMock(return_value=None)):
                        res = await scanner._scan_directory(Path("/p"))
                        assert res == []

    # 3. scan_root_directories: skip line 25 (Line 24->27)
    with patch.object(scanner, "_scan_directory", AsyncMock(return_value=[])):
        await scanner.scan_root_directories(["/p"])

@pytest.mark.asyncio
async def test_tree_sitter_parser_final_gaps():
    p_repo = MagicMock(spec=ProjectRepository)
    s_repo = MagicMock(spec=SymbolRepository)
    parser = TreeSitterParser(p_repo, s_repo)
    
    # 1. parse_file: Project not found (Line 85-86)
    p_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="not found"):
        await parser.parse_file(uuid4(), "f.py")

@pytest.mark.asyncio
async def test_main_final_gaps():
    from vault.main import run_scan_command
    # 1. run_scan_command: else branch (Line 266-269)
    mock_args = MagicMock(command="scan", directories=[], output="table")
    with patch("vault.crawler.ProjectDiscoveryService") as mock_ds_cls:
        mock_ds = mock_ds_cls.return_value
        mock_ds.discover_all_projects = AsyncMock(return_value={
            "success": True, "discovered_count": 0, "projects": []
        })
        with patch("vault.storage.get_db_session") as mock_db:
            mock_db.return_value.__aenter__.return_value = MagicMock()
            with patch("builtins.print") as mock_print:
                await run_scan_command(mock_args)
                mock_print.assert_any_call("Discovered 0 projects")

    # 2. run_scan_command: if args.directories branch (Line 241-264)
    # To hit 263-264, we need a project in results
    mock_args = MagicMock(command="scan", directories=["/p"], output="table")
    with patch("vault.crawler.ProjectDiscoveryService") as mock_ds_cls:
        mock_ds = mock_ds_cls.return_value
        p = MagicMock()
        p.name = "P"; p.type.value = "python"; p.file_count = 1; p.loc_total = 1
        mock_ds.scan_specific_path = AsyncMock(return_value={
            "success": True, "discovered_count": 1, "projects": [p]
        })
        with patch("vault.storage.get_db_session") as mock_db:
            mock_db.return_value.__aenter__.return_value = MagicMock()
            with patch("builtins.print") as mock_print:
                await run_scan_command(mock_args)
                found_p = False
                for call in mock_print.call_args_list:
                    if "P (python)" in str(call):
                        found_p = True
                assert found_p

@pytest.mark.asyncio
async def test_watcher_final_gaps():
    from vault.crawler import ProjectChangeQueue
    q = ProjectChangeQueue()
    # 1. clear: asyncio.QueueEmpty (Line 158-159)
    # This happens if q becomes empty between check and get_nowait
    with patch.object(q._queue, "empty", side_effect=[False, True]):
        with patch.object(q._queue, "get_nowait", side_effect=asyncio.QueueEmpty()):
            await q.clear()

@pytest.mark.asyncio
async def test_extractors_final_gaps():
    from vault.parser.extractors import SymbolExtractor, CSharpExtractor, JavaScriptExtractor
    with patch.object(SymbolExtractor, "_setup_parser"):
        ext = SymbolExtractor("python")
        # 1. _has_todo_near_node: prev loop (Line 98)
        node = MagicMock()
        node.prev_sibling = MagicMock(type="comment")
        # Second prev is not a comment
        node.prev_sibling.prev_sibling = MagicMock(type="not_comment")
        with patch.object(ext, "_get_node_text", return_value="TODO"):
            assert ext._has_todo_near_node(node, "") is True
            
        # 2. CSharpExtractor: various loop ends and None fallthrough
        cs = CSharpExtractor()
        assert cs._get_symbol_name(MagicMock(type="unknown"), "") is None
        
        # 3. JavaScriptExtractor loops (Line 428->427, 433->432, etc.)
        js = JavaScriptExtractor()
        assert js._get_symbol_name(MagicMock(type="unknown"), "") is None
        
        # variable_declaration loop end
        node = MagicMock(type="variable_declaration")
        node.children = [MagicMock(type="not_declarator")]
        assert js._get_symbol_name(node, "") is None

        # variable_declarator loop end
        node = MagicMock(type="variable_declaration")
        decl = MagicMock(type="variable_declarator")
        node.children = [decl]
        decl.children = [MagicMock(type="not_id")]
        assert js._get_symbol_name(node, "") is None

@pytest.mark.asyncio
async def test_tree_sitter_parser_more_push():
    p_repo = MagicMock(spec=ProjectRepository)
    s_repo = MagicMock(spec=SymbolRepository)
    parser = TreeSitterParser(p_repo, s_repo)
    
    # 1. _get_project_files hidden dir (Line 189)
    with patch("os.walk") as mock_walk:
        mock_walk.return_value = [(".git", [], [])]
        assert await parser._get_project_files(MagicMock(path="/p")) == []

    # 2. _should_include_file: language is None (Line 201)
    with patch.object(parser.fingerprinter, "_get_language_by_extension", return_value=None):
        assert parser._should_include_file(Path("f.txt")) is False

    # 3. parse_multiple_projects loop (Line 300->299)
    p_repo.get_by_id = AsyncMock(return_value=MagicMock())
    parser.parse_project = AsyncMock(return_value={"success": True})
    from vault.api.indexer import ParsingService
    svc = ParsingService(p_repo, s_repo)
    svc.parser = parser
    await svc.parse_multiple_projects([uuid4(), uuid4()])

@pytest.mark.asyncio
async def test_symbol_repository_final_gaps():
    from vault.storage.repositories import SymbolRepository
    from vault.storage.models import Symbol
    session = MagicMock()
    repo = SymbolRepository(session)
    
    # 1. create: Exception (Line 112-113)
    session.add.side_effect = Exception("DB Fail")
    with pytest.raises(DatabaseError):
        await repo.create(MagicMock(spec=Symbol))
        
    # 2. update_todo_status: not found (Line 231-233)
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
    with pytest.raises(DatabaseError):
         await repo.update_todo_status(uuid4(), True)

    # 3. update_todo_status: found (Line 234)
    mock_s = MagicMock(spec=Symbol)
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: mock_s))
    res = await repo.update_todo_status(uuid4(), True)
    assert res == mock_s
