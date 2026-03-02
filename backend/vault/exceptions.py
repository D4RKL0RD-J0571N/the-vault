"""Custom exception classes for The Vault application."""


class VaultError(Exception):
    """Base exception class for all Vault application errors."""
    
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DatabaseError(VaultError):
    """Raised when database operations fail."""
    pass


class ParsingError(VaultError):
    """Raised when code parsing fails."""
    pass


class ProjectNotFoundError(VaultError):
    """Raised when a requested project is not found."""
    pass


class SymbolNotFoundError(VaultError):
    """Raised when a requested symbol is not found."""
    pass


class ConfigurationError(VaultError):
    """Raised when configuration is invalid."""
    pass
