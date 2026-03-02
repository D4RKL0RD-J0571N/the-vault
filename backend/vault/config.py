"""Configuration management for The Vault application."""

import os
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database configuration
    database_url: str = Field(
        default="sqlite:///./vault.db",
        description="Database connection URL"
    )
    
    # Root directories to scan for projects
    root_directories: List[str] = Field(
        default_factory=list,
        description="List of root directories to scan for projects"
    )
    
    # File exclusion patterns
    exclude_patterns: List[str] = Field(
        default_factory=lambda: [
            ".git",
            "node_modules",
            "__pycache__",
            ".vscode",
            ".idea",
            "build",
            "dist",
            "target",
            "bin",
            "obj",
            ".venv",
            "venv",
            "env"
        ],
        description="File and directory patterns to exclude from scanning"
    )
    
    # File extensions to include by language
    language_extensions: dict = Field(
        default_factory=lambda: {
            "csharp": [".cs"],
            "java": [".java"],
            "python": [".py"],
            "javascript": [".js", ".ts", ".jsx", ".tsx"],
            "renpy": [".rpy", ".rpyc"],
            "typescript": [".ts", ".tsx"]
        },
        description="File extensions mapped to programming languages"
    )
    
    # Project detection markers
    project_markers: dict = Field(
        default_factory=lambda: {
            "unity": ["Assets/", "ProjectSettings/", "*.sln"],
            "java": ["pom.xml", "src/main/java/", "*.java"],
            "python": ["requirements.txt", "setup.py", "pyproject.toml", "*.py"],
            "node": ["package.json", "node_modules/", "*.js", "*.ts"],
            "renpy": ["game/*.rpy", "renpy/", "*.rpy"],
            "csharp": ["*.csproj", "*.sln", "*.cs"]
        },
        description="Markers to detect project types"
    )
    
    # Development vs production
    environment: str = Field(
        default="development",
        description="Application environment (development/production)"
    )
    
    # Logging configuration
    log_level: str = Field(
        default="DEBUG",
        description="Logging level"
    )
    
    # Parser settings
    max_file_size_mb: int = Field(
        default=10,
        description="Maximum file size to parse in MB"
    )
    
    # API settings
    api_host: str = Field(
        default="127.0.0.1",
        description="API server host"
    )
    
    api_port: int = Field(
        default=8000,
        description="API server port"
    )
    
    @field_validator("root_directories", mode="before")
    @classmethod
    def parse_root_directories(cls, v):
        """Parse root directories from string or list."""
        if isinstance(v, str):
            return [d.strip() for d in v.split(",") if d.strip()]
        return v
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment value."""
        if v not in ["development", "production", "test"]:
            raise ValueError(f"Environment must be one of: development, production, test")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    model_config = {
        "env_prefix": "VAULT_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }


# Global settings instance
settings = Settings()
