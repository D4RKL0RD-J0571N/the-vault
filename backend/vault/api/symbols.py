"""FastAPI routes for symbol management."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from vault.api.schemas import (
    Symbol,
    SymbolList,
    SymbolQuery,
    SymbolStatisticsResponse,
)
from vault.exceptions import ProjectNotFoundError, SymbolNotFoundError
from vault.parser import ParsingService
from vault.storage import get_db
from vault.storage.models import SymbolType
from vault.storage.repositories import ProjectRepository, SymbolRepository


router = APIRouter(prefix="/symbols", tags=["symbols"])


async def get_symbol_repository(db: AsyncSession = Depends(get_db)) -> SymbolRepository:
    """Dependency to get symbol repository."""
    return SymbolRepository(db)


async def get_project_repository(db: AsyncSession = Depends(get_db)) -> ProjectRepository:
    """Dependency to get project repository."""
    return ProjectRepository(db)


async def get_parsing_service(
    project_repo: ProjectRepository = Depends(get_project_repository),
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
) -> ParsingService:
    """Dependency to get parsing service."""
    return ParsingService(project_repo, symbol_repo)


@router.get("/project/{project_id}", response_model=SymbolList)
async def get_project_symbols(
    project_id: UUID,
    symbol_type: SymbolType = Query(None, description="Filter by symbol type"),
    file_path: str = Query(None, description="Filter by file path"),
    search: str = Query(None, description="Search in symbol names"),
    has_todo: bool = Query(None, description="Filter symbols with TODOs"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(1000, ge=1, le=10000, description="Items per page"),
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
    project_repo: ProjectRepository = Depends(get_project_repository),
) -> SymbolList:
    """Get symbols for a specific project with optional filtering."""
    try:
        # Verify project exists
        project = await project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")


        
        # Get symbols
        symbols = await symbol_repo.get_by_project(
            project_id, 
            symbol_type=symbol_type,
            limit=page_size,
            offset=(page - 1) * page_size
        )
        
        # Apply additional filters
        if file_path:
            symbols = [s for s in symbols if s.file_path == file_path]
        
        if search:
            search_lower = search.lower()
            symbols = [s for s in symbols if search_lower in s.name.lower()]
        
        if has_todo is not None:
            symbols = [s for s in symbols if s.has_todo == has_todo]
        
        # Apply pagination
        total = len(symbols)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_symbols = symbols[start_idx:end_idx]
        
        return SymbolList(
            symbols=paginated_symbols,
            total=total,
            page=page,
            page_size=page_size,
        )
        
    except HTTPException:
        raise
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get symbols: {e}")


@router.get("/project/{project_id}/file/{file_path:path}", response_model=List[Symbol])
async def get_file_symbols(
    project_id: UUID,
    file_path: str,
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
    project_repo: ProjectRepository = Depends(get_project_repository),
) -> List[Symbol]:
    """Get all symbols in a specific file."""
    try:
        # Verify project exists
        project = await project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        symbols = await symbol_repo.get_by_file(project_id, file_path)
        return symbols
        
    except HTTPException:
        raise
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file symbols: {e}")


@router.get("/project/{project_id}/search", response_model=List[Symbol])
async def search_symbols(
    project_id: UUID,
    query: str = Query(..., description="Search query"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
    project_repo: ProjectRepository = Depends(get_project_repository),
) -> List[Symbol]:
    """Search symbols by name pattern."""
    try:
        # Verify project exists
        project = await project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        symbols = await symbol_repo.search_by_name(project_id, query, limit)
        return symbols
        
    except HTTPException:
        raise
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search symbols: {e}")


@router.get("/project/{project_id}/todos", response_model=List[Symbol])
async def get_symbols_with_todos(
    project_id: UUID,
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
    project_repo: ProjectRepository = Depends(get_project_repository),
) -> List[Symbol]:
    """Get all symbols that contain TODO comments."""
    try:
        # Verify project exists
        project = await project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        symbols = await symbol_repo.get_symbols_with_todos(project_id)
        return symbols
        
    except HTTPException:
        raise
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get TODO symbols: {e}")


@router.get("/{symbol_id}", response_model=Symbol)
async def get_symbol(
    symbol_id: UUID,
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
) -> Symbol:
    """Get a specific symbol by ID."""
    try:
        symbol = await symbol_repo.get_by_id(symbol_id)
        if not symbol:
            raise HTTPException(status_code=404, detail="Symbol not found")
        
        return symbol
        
    except HTTPException:
        raise
    except SymbolNotFoundError:
        raise HTTPException(status_code=404, detail="Symbol not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get symbol: {e}")


@router.get("/project/{project_id}/statistics", response_model=SymbolStatisticsResponse)
async def get_symbol_statistics(
    project_id: UUID,
    parsing_service: ParsingService = Depends(get_parsing_service),
) -> SymbolStatisticsResponse:
    """Get symbol statistics for a project."""
    try:
        stats = await parsing_service.parser.get_parsing_statistics(project_id)
        
        return SymbolStatisticsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get symbol statistics: {e}")


@router.delete("/project/{project_id}")
async def delete_project_symbols(
    project_id: UUID,
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
    project_repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    """Delete all symbols for a project."""
    try:
        # Verify project exists
        project = await project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        deleted_count = await symbol_repo.delete_by_project(project_id)
        
        return {
            "message": f"Deleted {deleted_count} symbols for project {project_id}",
            "deleted_count": deleted_count,
        }
        
    except HTTPException:
        raise
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete symbols: {e}")


@router.delete("/project/{project_id}/file/{file_path:path}")
async def delete_file_symbols(
    project_id: UUID,
    file_path: str,
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
    project_repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    """Delete all symbols in a specific file."""
    try:
        # Verify project exists
        project = await project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        deleted_count = await symbol_repo.delete_by_file(project_id, file_path)
        
        return {
            "message": f"Deleted {deleted_count} symbols in file {file_path}",
            "deleted_count": deleted_count,
        }
        
    except HTTPException:
        raise
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file symbols: {e}")
