"""FastAPI routes for project management."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from vault.api.schemas import (
    Project,
    ProjectCreate,
    ProjectList,
    ProjectQuery,
    ProjectUpdate,
    ScanRequest,
    ScanResponse,
    StatisticsResponse,
)
from vault.crawler import ProjectDiscoveryService
from vault.exceptions import ProjectNotFoundError
from vault.storage import get_db
from vault.storage.models import ProjectType, IndexStatus
from vault.storage.repositories import ProjectRepository


router = APIRouter(prefix="/projects", tags=["projects"])


async def get_project_repository(db: AsyncSession = Depends(get_db)) -> ProjectRepository:
    """Dependency to get project repository."""
    return ProjectRepository(db)


async def get_discovery_service(
    project_repo: ProjectRepository = Depends(get_project_repository)
) -> ProjectDiscoveryService:
    """Dependency to get project discovery service."""
    return ProjectDiscoveryService(project_repo)


@router.get("/", response_model=ProjectList)
async def list_projects(
    project_type: Optional[ProjectType] = Query(None, alias="type", description="Filter by project type"),
    status: Optional[IndexStatus] = Query(None, description="Filter by indexing status"),
    search: str = Query(None, description="Search in project names"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page"),
    project_repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectList:
    """List all projects with optional filtering and pagination."""
    try:
        # Apply filters
        if project_type:
            projects = await project_repo.get_by_type(project_type)
        elif status:
            projects = await project_repo.get_by_status(status)
        else:
            projects = await project_repo.get_all()
        
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            projects = [p for p in projects if search_lower in p.name.lower()]
        
        # Apply pagination
        total = len(projects)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_projects = projects[start_idx:end_idx]
        
        return ProjectList(
            projects=paginated_projects,
            total=total,
            page=page,
            page_size=page_size,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {e}")


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: UUID,
    project_repo: ProjectRepository = Depends(get_project_repository),
) -> Project:
    """Get a specific project by ID."""
    try:
        project = await project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return project
        
    except HTTPException:
        raise
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project: {e}")


@router.post("/scan", response_model=ScanResponse)
async def scan_projects(
    request: ScanRequest,
    discovery_service: ProjectDiscoveryService = Depends(get_discovery_service),
) -> ScanResponse:
    """Scan for projects in configured directories."""
    try:
        if request.root_directories:
            # Scan specific directories
            results = []
            total_discovered = 0
            
            for root_dir in request.root_directories:
                result = await discovery_service.scan_specific_path(root_dir)
                if result["success"]:
                    results.extend(result["projects"])
                    total_discovered += result["discovered_count"]
            
            return ScanResponse(
                success=True,
                discovered_count=total_discovered,
                projects=results,
            )
        else:
            # Scan all configured directories
            result = await discovery_service.discover_all_projects()
            
            return ScanResponse(
                success=True,
                discovered_count=result["discovered_count"],
                projects=result["projects"],
            )
            
    except Exception as e:
        return ScanResponse(
            success=False,
            discovered_count=0,
            projects=[],
            error=str(e),
        )


@router.put("/{project_id}", response_model=Project)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    project_repo: ProjectRepository = Depends(get_project_repository),
) -> Project:
    """Update a project."""
    try:
        # Filter out None values
        update_data = project_update.model_dump(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updated_project = await project_repo.update(project_id, **update_data)
        return updated_project
        
    except HTTPException:
        raise
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update project: {e}")


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    project_repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    """Delete a project and all its symbols."""
    try:
        success = await project_repo.delete(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"message": "Project deleted successfully"}
        
    except HTTPException:
        raise
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {e}")


@router.get("/statistics/overview", response_model=StatisticsResponse)
async def get_project_statistics(
    discovery_service: ProjectDiscoveryService = Depends(get_discovery_service),
) -> StatisticsResponse:
    """Get overall project statistics."""
    try:
        stats = await discovery_service.get_project_statistics()
        
        return StatisticsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {e}")


@router.post("/{project_id}/refresh", response_model=Project)
async def refresh_project(
    project_id: UUID,
    discovery_service: ProjectDiscoveryService = Depends(get_discovery_service),
) -> Project:
    """Refresh project metadata by rescanning the directory."""
    try:
        # This would need to be implemented in the discovery service
        # For now, we'll return an error
        raise HTTPException(
            status_code=501, 
            detail="Project refresh not yet implemented"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh project: {e}")

