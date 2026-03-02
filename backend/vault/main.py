"""Main FastAPI application entry point for The Vault."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from vault.api import indexer_router, projects_router, symbols_router
from vault.api.schemas import ErrorResponse, HealthResponse
from vault.config import settings
from vault.exceptions import VaultError
from vault.storage import init_db
from vault.storage.repositories import ProjectRepository



# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.environment == "production"
        else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting The Vault API server")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # TODO: Start file watcher if configured
        # TODO: Initialize other services
        
        yield
        
    except Exception as e:
        logger.error("Failed to initialize application", error=str(e))
        raise
    
    # Shutdown
    logger.info("Shutting down The Vault API server")
    # TODO: Cleanup services


# Create FastAPI application
app = FastAPI(
    title="The Vault API",
    description="AI-powered code archaeology desktop application API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
)

# Add CORS middleware for Tauri frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost:3000"],  # Tauri dev origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(VaultError)
async def vault_exception_handler(request, exc: VaultError):
    """Handle custom Vault exceptions."""
    logger.error(
        "Vault application error",
        error=exc.message,
        details=exc.details,
        path=request.url.path,
    )
    
    return JSONResponse(
        status_code=500,
        content=jsonable_encoder(
            ErrorResponse(
                detail=exc.message,
                details=exc.details,
                timestamp=datetime.now(timezone.utc),
            )
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(
            ErrorResponse(
                detail=exc.detail,
                timestamp=datetime.now(timezone.utc),
            )
        ),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        exc_info=True,
        path=request.url.path,
    )
    
    return JSONResponse(
        status_code=500,
        content=jsonable_encoder(
            ErrorResponse(
                detail="Internal server error",
                timestamp=datetime.now(timezone.utc),
            )
        ),
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
    )


# Include routers
app.include_router(projects_router)
app.include_router(symbols_router)
app.include_router(indexer_router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with basic information."""
    return {
        "name": "The Vault API",
        "version": "0.1.0",
        "description": "AI-powered code archaeology desktop application API",
        "docs_url": "/docs" if settings.environment == "development" else None,
    }


# CLI entry point
async def cli():
    """Command-line interface for The Vault."""
    import argparse
    
    parser = argparse.ArgumentParser(description="The Vault - AI-powered code archaeology")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan directories for projects")
    scan_parser.add_argument(
        "directories", 
        nargs="*", 
        help="Directories to scan (optional, uses configured directories if not provided)"
    )
    scan_parser.add_argument(
        "--output", 
        choices=["json", "table"], 
        default="table",
        help="Output format"
    )
    
    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument(
        "--host", 
        default=settings.api_host,
        help=f"Host to bind to (default: {settings.api_host})"
    )
    serve_parser.add_argument(
        "--port", 
        type=int, 
        default=settings.api_port,
        help=f"Port to bind to (default: {settings.api_port})"
    )
    
    args = parser.parse_args()
    
    if args.command == "scan":
        await run_scan_command(args)
    elif args.command == "serve":
        await run_serve_command(args)
    else:
        parser.print_help()


async def run_scan_command(args):
    """Run the scan command."""
    from vault.crawler import ProjectDiscoveryService
    from vault.storage import get_db_session
    
    logger.info("Starting project scan")
    
    async with get_db_session() as db:
        project_repo = ProjectRepository(db)
        discovery_service = ProjectDiscoveryService(project_repo)
        
        if args.directories:
            # Scan specific directories
            results = []
            for directory in args.directories:
                result = await discovery_service.scan_specific_path(directory)
                if result["success"]:
                    results.extend(result["projects"])
                    print(f"Scanned {directory}: {result['discovered_count']} projects")
                else:
                    print(f"Error scanning {directory}: {result['error']}")
            
            print(f"\nTotal projects discovered: {len(results)}")
            
            if args.output == "json":
                import json
                print(json.dumps([{
                    "name": p.name,
                    "type": p.type.value,
                    "path": p.path,
                    "files": p.file_count,
                    "loc": p.loc_total,
                } for p in results], indent=2))
            else:
                for project in results:
                    print(f"  {project.name} ({project.type.value}) - {project.file_count} files, {project.loc_total} LOC")
        
        else:
            # Scan configured directories
            result = await discovery_service.discover_all_projects()
            print(f"Discovered {result['discovered_count']} projects")
            
            if args.output == "table":
                for project in result["projects"]:
                    print(f"  {project.name} ({project.type.value}) - {project.file_count} files, {project.loc_total} LOC")


async def run_serve_command(args):
    """Run the serve command."""
    import uvicorn
    
    logger.info(f"Starting server on {args.host}:{args.port}")
    
    config = uvicorn.Config(
        app,
        host=args.host,
        port=args.port,
        log_level=settings.log_level.lower(),
        access_log=True,
    )
    
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(cli())
