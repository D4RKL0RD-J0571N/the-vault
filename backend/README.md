# The Vault Backend

AI-powered code archaeology desktop application backend.

## Overview

The Vault is a local-first application that indexes personal development projects across multiple drives, extracts symbols from code files using tree-sitter, and provides semantic search capabilities. This backend provides the core scanning, parsing, and API functionality.

## Architecture

The backend follows a layered architecture:

- **API Layer** (`vault/api/`): FastAPI routes and Pydantic schemas
- **Parser Layer** (`vault/parser/`): Tree-sitter based symbol extraction
- **Crawler Layer** (`vault/crawler/`): Project discovery and file watching
- **Storage Layer** (`vault/storage/`): SQLAlchemy models and repositories

## Features

### Phase 1 (Current)
- **Project Discovery**: Automatically detect and categorize development projects
- **Symbol Extraction**: Parse C#, Java, Python, JavaScript, and RenPy code
- **REST API**: Complete API for project and symbol management
- **File Watching**: Monitor project changes for automatic re-indexing
- **SQLite Storage**: Local database with full-text search capabilities

### Supported Languages
- **C#** (Unity projects)
- **Java**
- **Python**
- **JavaScript/TypeScript**
- **RenPy** (visual novel engine)

## Quick Start

### Prerequisites
- Python 3.11+
- SQLite (included with Python)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd the-vault/backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the application:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Initialize the database:
```bash
python -m vault init-db
```

### Running the Application

#### Development Server
```bash
python -m vault serve
```

#### Production Server
```bash
uvicorn vault.main:app --host 0.0.0.0 --port 8000
```

### CLI Usage

#### Scan for Projects
```bash
# Scan configured directories
python -m vault scan

# Scan specific directories
python -m vault scan /path/to/projects /another/path

# Output as JSON
python -m vault scan --output json
```

#### API Documentation
When running in development mode, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuration

The application can be configured via environment variables or `.env` file:

```env
# Database
VAULT_DATABASE_URL=sqlite:///./vault.db

# Root directories to scan
VAULT_ROOT_DIRECTORIES=/path/to/projects,/another/path

# API server
VAULT_API_HOST=127.0.0.1
VAULT_API_PORT=8000

# Environment
VAULT_ENVIRONMENT=development
VAULT_LOG_LEVEL=DEBUG

# Parser settings
VAULT_MAX_FILE_SIZE_MB=10
```

## API Endpoints

### Projects
- `GET /projects/` - List all projects
- `GET /projects/{id}` - Get project details
- `POST /projects/scan` - Trigger project scanning
- `PUT /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project
- `GET /projects/statistics/overview` - Get project statistics

### Symbols
- `GET /symbols/project/{id}` - Get symbols for a project
- `GET /symbols/project/{id}/file/{path}` - Get symbols in a file
- `GET /symbols/project/{id}/search` - Search symbols
- `GET /symbols/project/{id}/todos` - Get symbols with TODOs
- `GET /symbols/{id}` - Get specific symbol

### Indexer
- `POST /indexer/projects/{id}/parse` - Start parsing project
- `POST /indexer/projects/batch-parse` - Parse multiple projects
- `GET /indexer/projects/{id}/status` - Get parsing status
- `POST /indexer/projects/{id}/cancel` - Cancel parsing
- `GET /indexer/status/active` - Get active parsing tasks

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=vault --cov-report=html

# Run specific test file
pytest tests/test_storage.py

# Run with verbose output
pytest -v
```

### Code Quality
```bash
# Lint code
ruff check vault/

# Format code
ruff format vault/

# Type checking
mypy vault/
```

### Project Structure
```
backend/
├── vault/
│   ├── api/           # FastAPI routes and schemas
│   ├── crawler/       # Project discovery and file watching
│   ├── parser/        # Tree-sitter symbol extraction
│   ├── storage/       # Database models and repositories
│   ├── config.py      # Configuration management
│   ├── exceptions.py  # Custom exception classes
│   └── main.py        # FastAPI application entry point
├── tests/             # Test suite
├── requirements.txt   # Python dependencies
├── pyproject.toml    # Project configuration
└── README.md         # This file
```

## Architecture Rules

1. **Strict Layer Separation**: Parser layer NEVER calls AI services
2. **Database Abstraction**: All database operations through repository pattern
3. **API Thinness**: FastAPI routes only handle HTTP concerns
4. **Async/Await**: All I/O operations are async
5. **Type Safety**: Type hints everywhere, Pydantic v2 for validation
6. **Error Handling**: Custom exception classes with proper HTTP status codes
7. **Logging**: Structured logging via structlog, no print() statements

## Database Schema

### Projects Table
- `id` (UUID, primary key)
- `name` (string) - Project name derived from folder
- `path` (string) - Absolute path on disk
- `type` (enum) - Unity, Java, Python, Node, RenPy, C#, Other
- `language_primary` (string) - Most common file extension
- `loc_total` (integer) - Total lines of code
- `file_count` (integer) - Number of source files
- `health_score` (float) - Composite health metric (0-1)
- `index_status` (enum) - Pending, Parsing, Complete, Error
- `git_has` (boolean) - Whether project has git repository

### Symbols Table
- `id` (UUID, primary key)
- `project_id` (UUID, foreign key)
- `file_path` (string) - Relative path within project
- `symbol_type` (enum) - Class, Method, Field, Enum, etc.
- `name` (string) - Symbol name
- `qualified_name` (string) - Fully qualified name
- `signature` (text) - Full method/class signature
- `line_start`, `line_end` (integers) - Symbol location
- `raw_code` (text) - Extracted source code
- `content_hash` (string) - MD5 for change detection
- `has_todo` (boolean) - Contains TODO/FIXME comments

## Performance Considerations

- **Batch Operations**: Symbol creation uses batch inserts for efficiency
- **Content Hashing**: MD5 hashes detect file changes without re-parsing
- **Async Processing**: All I/O operations are non-blocking
- **Memory Management**: Large files are skipped based on size limits
- **Database Indexing**: Proper indexes on frequently queried fields

## Troubleshooting

### Common Issues

1. **Tree-sitter Language Not Found**
   - Ensure `tree-sitter-languages` package is installed
   - Some languages may require additional setup

2. **Permission Errors**
   - Check file permissions on project directories
   - Ensure the application can read source files

3. **Memory Usage**
   - Adjust `VAULT_MAX_FILE_SIZE_MB` for large files
   - Monitor memory usage during large project scans

4. **Database Locks**
   - Ensure proper async/await usage
   - Check for long-running transactions

### Debug Mode

Enable debug logging:
```env
VAULT_ENVIRONMENT=development
VAULT_LOG_LEVEL=DEBUG
```

This will provide detailed logs for troubleshooting parsing and scanning issues.

## Contributing

1. Follow the existing code style and architecture rules
2. Add tests for new functionality
3. Update documentation for API changes
4. Ensure all tests pass before submitting

## License

MIT License - see LICENSE file for details.
