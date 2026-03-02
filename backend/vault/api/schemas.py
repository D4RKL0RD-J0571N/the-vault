"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from vault.storage.models import IndexStatus, ProjectType, SymbolType


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = {"from_attributes": True}


# Project schemas
class ProjectBase(BaseSchema):
    """Base project schema."""
    name: str = Field(..., description="Project name")
    path: str = Field(..., description="Absolute path to project")
    type: ProjectType = Field(..., description="Project type")
    language_primary: Optional[str] = Field(None, description="Primary programming language")
    loc_total: int = Field(0, description="Total lines of code")
    file_count: int = Field(0, description="Total number of files")
    language_counts: dict = Field(default_factory=dict, description="Files by language breakdown")
    first_seen: Optional[datetime] = Field(None, description="Oldest file timestamp")
    last_modified: Optional[datetime] = Field(None, description="Most recent file change")
    health_score: float = Field(0.0, description="Project health score (0-1)")
    index_status: IndexStatus = Field(IndexStatus.PENDING, description="Indexing status")
    git_has: bool = Field(False, description="Has git repository")


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    pass


class ProjectUpdate(BaseSchema):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, description="Project name")
    language_primary: Optional[str] = Field(None, description="Primary programming language")
    loc_total: Optional[int] = Field(None, description="Total lines of code")
    file_count: Optional[int] = Field(None, description="Total number of files")
    first_seen: Optional[datetime] = Field(None, description="Oldest file timestamp")
    last_modified: Optional[datetime] = Field(None, description="Most recent file change")
    health_score: Optional[float] = Field(None, description="Project health score (0-1)")
    index_status: Optional[IndexStatus] = Field(None, description="Indexing status")
    git_has: Optional[bool] = Field(None, description="Has git repository")


class Project(ProjectBase):
    """Complete project schema."""
    id: UUID = Field(..., description="Project ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ProjectList(BaseSchema):
    """Schema for project list response."""
    projects: List[Project] = Field(..., description="List of projects")
    total: int = Field(..., description="Total number of projects")
    page: int = Field(1, description="Current page")
    page_size: int = Field(100, description="Items per page")


# Symbol schemas
class SymbolBase(BaseSchema):
    """Base symbol schema."""
    file_path: str = Field(..., description="Relative file path")
    symbol_type: SymbolType = Field(..., description="Symbol type")
    name: str = Field(..., description="Symbol name")
    qualified_name: str = Field(..., description="Fully qualified symbol name")
    signature: Optional[str] = Field(None, description="Symbol signature")
    line_start: int = Field(..., description="Starting line number")
    line_end: int = Field(..., description="Ending line number")
    raw_code: Optional[str] = Field(None, description="Raw source code")
    content_hash: str = Field(..., description="Content hash for change detection")
    has_todo: bool = Field(False, description="Contains TODO comments")


class SymbolCreate(SymbolBase):
    """Schema for creating a symbol."""
    project_id: UUID = Field(..., description="Project ID")


class Symbol(SymbolBase):
    """Complete symbol schema."""
    id: UUID = Field(..., description="Symbol ID")
    project_id: UUID = Field(..., description="Project ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class SymbolList(BaseSchema):
    """Schema for symbol list response."""
    symbols: List[Symbol] = Field(..., description="List of symbols")
    total: int = Field(..., description="Total number of symbols")
    page: int = Field(1, description="Current page")
    page_size: int = Field(1000, description="Items per page")


# API request/response schemas
class ScanRequest(BaseSchema):
    """Schema for scan request."""
    root_directories: Optional[List[str]] = Field(None, description="Root directories to scan")


class ScanResponse(BaseSchema):
    """Schema for scan response."""
    success: bool = Field(..., description="Scan success status")
    discovered_count: int = Field(..., description="Number of projects discovered")
    projects: List[Project] = Field(..., description="Discovered projects")
    error: Optional[str] = Field(None, description="Error message if failed")


class ParseRequest(BaseSchema):
    """Schema for parse request."""
    project_ids: Optional[List[UUID]] = Field(None, description="Specific project IDs to parse")


class ParseResponse(BaseSchema):
    """Schema for parse response."""
    success: bool = Field(..., description="Parse success status")
    message: str = Field(..., description="Response message")
    project_id: Optional[UUID] = Field(None, description="Project ID")
    projects_attempted: Optional[int] = Field(None, description="Number of projects attempted")
    successful: Optional[int] = Field(None, description="Number of successful parses")
    failed: Optional[int] = Field(None, description="Number of failed parses")


class StatusResponse(BaseSchema):
    """Schema for status response."""
    success: bool = Field(..., description="Status request success")
    project_id: UUID = Field(..., description="Project ID")
    status: str = Field(..., description="Project status")
    is_parsing: bool = Field(..., description="Whether project is currently being parsed")


class StatisticsResponse(BaseSchema):
    """Schema for statistics response."""
    total_projects: int = Field(..., description="Total number of projects")
    by_type: dict = Field(..., description="Projects by type")
    by_status: dict = Field(..., description="Projects by status")
    total_files: int = Field(..., description="Total files across all projects")
    total_loc: int = Field(..., description="Total lines of code across all projects")


class SymbolStatisticsResponse(BaseSchema):
    """Schema for symbol statistics response."""
    project_id: UUID = Field(..., description="Project ID")
    project_name: str = Field(..., description="Project name")
    total_symbols: int = Field(..., description="Total symbols in project")
    symbol_counts: dict = Field(..., description="Symbols by type")
    todo_count: int = Field(..., description="Number of symbols with TODOs")
    last_parsed: datetime = Field(..., description="Last parse timestamp")


class HealthResponse(BaseSchema):
    """Schema for health check response."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Response timestamp")
    version: str = Field("0.1.0", description="API version")


class ErrorResponse(BaseSchema):
    """Schema for error responses."""
    detail: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    timestamp: datetime = Field(..., description="Error timestamp")


# Query parameters
class ProjectQuery(BaseSchema):
    """Query parameters for project endpoints."""
    type: Optional[ProjectType] = Field(None, description="Filter by project type")
    status: Optional[IndexStatus] = Field(None, description="Filter by indexing status")
    search: Optional[str] = Field(None, description="Search in project names")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(100, ge=1, le=1000, description="Items per page")


class SymbolQuery(BaseSchema):
    """Query parameters for symbol endpoints."""
    symbol_type: Optional[SymbolType] = Field(None, description="Filter by symbol type")
    file_path: Optional[str] = Field(None, description="Filter by file path")
    search: Optional[str] = Field(None, description="Search in symbol names")
    has_todo: Optional[bool] = Field(None, description="Filter symbols with TODOs")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(1000, ge=1, le=10000, description="Items per page")
