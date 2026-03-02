"""Repository pattern for database operations."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from vault.exceptions import (DatabaseError, ProjectNotFoundError,
                              SymbolNotFoundError)
from vault.storage.models import (IndexStatus, Project, ProjectType, Symbol,
                                  SymbolType)


class BaseRepository:
    """Base repository with common database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session


class ProjectRepository(BaseRepository):
    """Repository for Project operations."""

    async def create(self, project: Project) -> Project:
        """Create a new project."""
        try:
            self.session.add(project)
            await self.session.flush()
            await self.session.refresh(project)
            return project
        except Exception as e:
            raise DatabaseError(f"Failed to create project: {e}")

    async def get_by_id(self, project_id: UUID) -> Optional[Project]:
        """Get project by ID."""
        # Convert UUID to string for comparison since UUIDs are stored as strings in SQLite
        project_id_str = str(project_id)
        result = await self.session.execute(
            select(Project).where(Project.id == project_id_str)
        )
        return result.scalar_one_or_none()

    async def get_by_path(self, path: str) -> Optional[Project]:
        """Get project by file path."""
        result = await self.session.execute(select(Project).where(Project.path == path))
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Project]:
        """Get all projects with pagination."""
        result = await self.session.execute(
            select(Project)
            .order_by(Project.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def update(self, project_id: UUID, **kwargs) -> Project:
        """Update project fields."""
        try:
            # Convert UUID to string for comparison since UUIDs are stored as strings in SQLite
            project_id_str = str(project_id)
            stmt = update(Project).where(Project.id == project_id_str).values(**kwargs)
            await self.session.execute(stmt)
            await self.session.flush()

            project = await self.get_by_id(project_id)
            if not project:
                raise ProjectNotFoundError(f"Project {project_id} not found")
            return project
        except ProjectNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to update project: {e}")

    async def delete(self, project_id: UUID) -> bool:
        """Delete a project and all its symbols."""
        try:
            # Convert UUID to string for comparison since UUIDs are stored as strings in SQLite
            project_id_str = str(project_id)
            stmt = delete(Project).where(Project.id == project_id_str)
            result = await self.session.execute(stmt)
            return result.rowcount > 0
        except Exception as e:
            raise DatabaseError(f"Failed to delete project: {e}")

    async def get_by_type(self, project_type: ProjectType) -> List[Project]:
        """Get projects by type."""
        result = await self.session.execute(
            select(Project).where(Project.type == project_type)
        )
        return result.scalars().all()

    async def get_by_status(self, status: IndexStatus) -> List[Project]:
        """Get projects by indexing status."""
        result = await self.session.execute(
            select(Project).where(Project.index_status == status)
        )
        return result.scalars().all()

    async def update_status(self, project_id: UUID, status: IndexStatus) -> Project:
        """Update project indexing status."""
        return await self.update(project_id, index_status=status)


class SymbolRepository(BaseRepository):
    """Repository for Symbol operations."""

    async def create(self, symbol: Symbol) -> Symbol:
        """Create a new symbol."""
        try:
            self.session.add(symbol)
            await self.session.flush()
            await self.session.refresh(symbol)
            return symbol
        except Exception as e:
            raise DatabaseError(f"Failed to create symbol: {e}")

    async def create_batch(self, symbols: List[Symbol]) -> List[Symbol]:
        """Create multiple symbols efficiently."""
        try:
            self.session.add_all(symbols)
            await self.session.flush()
            # Refresh all symbols to get their IDs
            for symbol in symbols:
                await self.session.refresh(symbol)
            return symbols
        except Exception as e:
            raise DatabaseError(f"Failed to create symbols batch: {e}")

    async def get_by_id(self, symbol_id: UUID) -> Optional[Symbol]:
        """Get symbol by ID."""
        # Convert UUID to string for comparison since UUIDs are stored as strings in SQLite
        symbol_id_str = str(symbol_id)
        result = await self.session.execute(
            select(Symbol).where(Symbol.id == symbol_id_str)
        )
        return result.scalar_one_or_none()

    async def get_by_project(
        self,
        project_id: UUID,
        symbol_type: Optional[SymbolType] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Symbol]:
        """Get symbols for a project, optionally filtered by type."""
        # Convert UUID to string for comparison since UUIDs are stored as strings in SQLite
        project_id_str = str(project_id)
        query = select(Symbol).where(Symbol.project_id == project_id_str)

        if symbol_type:
            query = query.where(Symbol.symbol_type == symbol_type)

        query = (
            query.order_by(Symbol.file_path, Symbol.line_start)
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_file(self, project_id: UUID, file_path: str) -> List[Symbol]:
        """Get all symbols in a specific file."""
        # Convert UUID to string for comparison since UUIDs are stored as strings in SQLite
        project_id_str = str(project_id)
        result = await self.session.execute(
            select(Symbol)
            .where(
                and_(Symbol.project_id == project_id_str, Symbol.file_path == file_path)
            )
            .order_by(Symbol.line_start)
        )
        return result.scalars().all()

    async def search_by_name(
        self, project_id: UUID, name_pattern: str, limit: int = 100
    ) -> List[Symbol]:
        """Search symbols by name pattern."""
        # Convert UUID to string for comparison since UUIDs are stored as strings in SQLite
        project_id_str = str(project_id)
        result = await self.session.execute(
            select(Symbol)
            .where(
                and_(
                    Symbol.project_id == project_id_str,
                    Symbol.name.ilike(f"%{name_pattern}%"),
                )
            )
            .limit(limit)
        )
        return result.scalars().all()

    async def delete_by_project(self, project_id: UUID) -> int:
        """Delete all symbols for a project."""
        try:
            # Convert UUID to string for comparison since UUIDs are stored as strings in SQLite
            project_id_str = str(project_id)
            stmt = delete(Symbol).where(Symbol.project_id == project_id_str)
            result = await self.session.execute(stmt)
            return result.rowcount
        except Exception as e:
            raise DatabaseError(f"Failed to delete symbols for project: {e}")

    async def delete_by_file(self, project_id: UUID, file_path: str) -> int:
        """Delete all symbols in a specific file."""
        try:
            # Convert UUID to string for comparison since UUIDs are stored as strings in SQLite
            project_id_str = str(project_id)
            stmt = delete(Symbol).where(
                and_(Symbol.project_id == project_id_str, Symbol.file_path == file_path)
            )
            result = await self.session.execute(stmt)
            return result.rowcount
        except Exception as e:
            raise DatabaseError(f"Failed to delete file symbols: {e}")

    async def get_symbols_with_todos(self, project_id: UUID) -> List[Symbol]:
        """Get all symbols that contain TODO comments."""
        # Convert UUID to string for comparison since UUIDs are stored as strings in SQLite
        project_id_str = str(project_id)
        result = await self.session.execute(
            select(Symbol).where(
                and_(Symbol.project_id == project_id_str, Symbol.has_todo == True)
            )
        )
        return result.scalars().all()

    async def update_todo_status(self, symbol_id: UUID, has_todo: bool) -> Symbol:
        """Update TODO status of a symbol."""
        try:
            # Convert UUID to string for comparison since UUIDs are stored as strings in SQLite
            symbol_id_str = str(symbol_id)
            stmt = (
                update(Symbol)
                .where(Symbol.id == symbol_id_str)
                .values(has_todo=has_todo)
                .returning(Symbol)
            )
            result = await self.session.execute(stmt)
            symbol = result.scalar_one_or_none()
            if not symbol:
                raise SymbolNotFoundError(f"Symbol {symbol_id} not found")
            return symbol
        except SymbolNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to update symbol TODO status: {e}")
