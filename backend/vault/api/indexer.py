"""FastAPI routes for indexing and parsing operations."""

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from vault.api.schemas import ParseRequest, ParseResponse, StatusResponse
from vault.exceptions import ProjectNotFoundError
from vault.parser import ParsingService
from vault.storage import get_db
from vault.storage.repositories import ProjectRepository, SymbolRepository

router = APIRouter(prefix="/indexer", tags=["indexer"])


async def get_project_repository(
    db: AsyncSession = Depends(get_db),
) -> ProjectRepository:
    """Dependency to get project project repository."""
    return ProjectRepository(db)


async def get_symbol_repository(db: AsyncSession = Depends(get_db)) -> SymbolRepository:
    """Dependency to get symbol repository."""
    return SymbolRepository(db)


async def get_parsing_service(
    project_repo: ProjectRepository = Depends(get_project_repository),
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
) -> ParsingService:
    """Dependency to get parsing service."""
    return ParsingService(project_repo, symbol_repo)


@router.post("/projects/{project_id}/parse", response_model=ParseResponse)
async def parse_project(
    project_id: UUID,
    parsing_service: ParsingService = Depends(get_parsing_service),
) -> ParseResponse:
    """Start parsing a specific project."""
    try:
        result = await parsing_service.start_parsing_project(project_id)

        return ParseResponse(
            success=result["success"],
            message=result["message"],
            project_id=project_id,
        )

    except Exception as e:
        return ParseResponse(
            success=False,
            message=f"Failed to start parsing: {e}",
            project_id=project_id,
        )


@router.post("/projects/batch-parse", response_model=ParseResponse)
async def parse_multiple_projects(
    request: ParseRequest,
    parsing_service: ParsingService = Depends(get_parsing_service),
) -> ParseResponse:
    """Parse multiple projects concurrently."""
    try:
        if not request.project_ids:
            raise HTTPException(status_code=400, detail="No project IDs provided")

        result = await parsing_service.parse_multiple_projects(request.project_ids)

        return ParseResponse(
            success=result["success"],
            message=f"Attempted to parse {result['projects_attempted']} projects",
            projects_attempted=result["projects_attempted"],
            successful=result["successful"],
            failed=result["failed"],
        )

    except HTTPException:
        raise
    except Exception as e:
        return ParseResponse(
            success=False,
            message=f"Failed to start batch parsing: {e}",
        )


@router.get("/projects/{project_id}/status", response_model=StatusResponse)
async def get_parsing_status(
    project_id: UUID,
    parsing_service: ParsingService = Depends(get_parsing_service),
) -> StatusResponse:
    """Get parsing status for a specific project."""
    try:
        result = await parsing_service.get_parsing_status(project_id)

        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])

        # Apply protection for .value if status is an Enum
        status_value = getattr(result["status"], "value", result["status"])

        return StatusResponse(
            success=True,
            project_id=project_id,
            status=status_value,
            is_parsing=result["is_parsing"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get parsing status: {e}"
        )


@router.post("/projects/{project_id}/cancel", response_model=ParseResponse)
async def cancel_parsing(
    project_id: UUID,
    parsing_service: ParsingService = Depends(get_parsing_service),
) -> ParseResponse:
    """Cancel an active parsing task for a project."""
    try:
        result = await parsing_service.cancel_parsing(project_id)

        return ParseResponse(
            success=result["success"],
            message=result["message"],
            project_id=project_id,
        )

    except Exception as e:
        return ParseResponse(
            success=False,
            message=f"Failed to cancel parsing: {e}",
            project_id=project_id,
        )


@router.get("/status/active", response_model=List[UUID])
async def get_active_parsing_tasks(
    parsing_service: ParsingService = Depends(get_parsing_service),
) -> List[UUID]:
    """Get list of projects currently being parsed."""
    try:
        active_tasks = await parsing_service.get_active_parsing_tasks()
        return active_tasks

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active tasks: {e}")


@router.get("/status/overview")
async def get_indexing_overview(
    project_repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    """Get overview of indexing status across all projects."""
    try:
        # Get all projects
        all_projects = await project_repo.get_all(limit=10000)

        # Count by status
        status_counts = {}
        total_projects = len(all_projects)

        for project in all_projects:
            status = getattr(project.index_status, "value", project.index_status)
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_projects": total_projects,
            "status_counts": status_counts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get overview: {e}")


@router.post("/reparse-file")
async def reparse_file(
    project_id: UUID,
    file_path: str = Query(..., description="Relative file path within project"),
    parsing_service: ParsingService = Depends(get_parsing_service),
) -> dict:
    """Reparse a specific file that has changed."""
    try:
        result = await parsing_service.parser.reparse_changed_file(
            project_id, file_path
        )

        return result

    except Exception as e:
        return {
            "success": False,
            "file_path": file_path,
            "error": str(e),
            "symbols_extracted": 0,
        }
