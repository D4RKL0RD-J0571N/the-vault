"""SQLAlchemy database models for The Vault application."""

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class ProjectType(str, Enum):
    """Supported project types."""

    UNITY = "unity"
    JAVA = "java"
    PYTHON = "python"
    NODE = "node"
    RENPY = "renpy"
    CSHARP = "csharp"
    OTHER = "other"


class IndexStatus(str, Enum):
    """Project indexing status."""

    PENDING = "pending"
    PARSING = "parsing"
    COMPLETE = "complete"
    ERROR = "error"


class SymbolType(str, Enum):
    """Supported symbol types."""

    CLASS = "class"
    METHOD = "method"
    FIELD = "field"
    ENUM = "enum"
    INTERFACE = "interface"
    PROPERTY = "property"
    CONSTRUCTOR = "constructor"
    CONSTANT = "constant"
    FUNCTION = "function"


class Project(Base):
    """Represents a development project."""

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    type: Mapped[ProjectType] = mapped_column(String(50), nullable=False)
    language_primary: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    loc_total: Mapped[int] = mapped_column(Integer, default=0)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    language_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    first_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_modified: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    health_score: Mapped[float] = mapped_column(Float, default=0.0)
    index_status: Mapped[IndexStatus] = mapped_column(
        String(20), default=IndexStatus.PENDING
    )
    git_has: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    symbols: Mapped[list["Symbol"]] = relationship(
        "Symbol", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, type={self.type})>"


class Symbol(Base):
    """Represents a code symbol (class, method, etc.) within a project."""

    __tablename__ = "symbols"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    symbol_type: Mapped[SymbolType] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    qualified_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    line_start: Mapped[int] = mapped_column(Integer, nullable=False)
    line_end: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    has_todo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="symbols")

    def __repr__(self) -> str:
        return (
            f"<Symbol(id={self.id}, name={self.name}, type={self.symbol_type}, "
            f"project_id={self.project_id})>"
        )

    @staticmethod
    def generate_content_hash(content: str) -> str:
        """Generate MD5 hash for content change detection."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()
