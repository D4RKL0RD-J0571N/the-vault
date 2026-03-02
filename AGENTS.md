# The Vault — Agent Context

## Project Identity

The Vault is a local-first, AI-powered code archaeology desktop application.
It indexes personal development projects across multiple drives, generates
AI documentation for every code symbol (class, method, enum, etc.) using a
local Ollama instance, and provides semantic search across the entire history.

## Tech Stack

- Backend:  FastAPI (Python 3.11+), SQLAlchemy, SQLite
- AI:       Ollama (WSL2, RTX 3060 12GB) — Qwen2.5-Coder 7B Instruct
- Vectors:  Qdrant (Docker) + nomic-embed-text for embeddings
- Parser:   tree-sitter (Python bindings) — C#, Java, Python, JS, RenPy
- Frontend: Tauri v2 + React 18 + TypeScript 5 + Tailwind CSS
- Storage:  SQLite (metadata), Qdrant (vectors), .vault/*.json (AI doc cache)

## Repository Structure

- backend/vault/         FastAPI application
- backend/vault/crawler/ File watcher and project scanner
- backend/vault/parser/  Tree-sitter symbol extraction
- backend/vault/ai/      Ollama client, doc generation queue
- backend/vault/storage/ SQLAlchemy models, Qdrant wrapper, JSON cache
- backend/vault/api/     FastAPI route handlers
- frontend/src/pages/    Tauri/React page components
- frontend/src/components/ Reusable UI components
- docs/                  Architecture docs, ADRs, API reference

## Architecture Rules — Never Violate These

1. The parser layer (tree-sitter) NEVER calls Ollama. These are separate layers.
2. Ollama is called ONLY from backend/vault/ai/ — nowhere else.
3. All file system access on the user's drives goes through the crawler module.
4. The .vault/ hidden folder in each project is append-only. Never delete user files.
5. All Qdrant operations go through storage/vector_store.py — never call Qdrant directly.
6. FastAPI routes are thin — business logic lives in the service layer, not in routes.
7. The frontend NEVER reads files directly — all data goes through the FastAPI API.

## Coding Conventions

### Python (backend)
- Use type hints everywhere. No `Any` without a comment explaining why.
- Async/await for all I/O — never blocking calls in async functions.
- Pydantic v2 for all data validation and API schemas.
- Error handling: use custom exception classes from vault/exceptions.py.
- Logging: use structured logging via `structlog`, never print().
- Tests: pytest, aim for coverage on parser and AI modules especially.

### TypeScript (frontend)
- Strict mode enabled. No `any` without comment.
- All API calls go through lib/api.ts — never raw fetch() in components.
- Component props must be typed with interfaces, not inline types.
- No business logic in components — hooks only.

## Current Build Phase

Phase: 1 — Scanner and Parser (complete)
Active branch: feat/project-scanner
Focus: backend/vault/crawler/ and backend/vault/parser/
Status: 98% test coverage achieved

## AI Assistant Configuration

When working with this codebase, AI assistants should:

1. **Read AGENTS.md first** - This file contains the complete project context
2. **Follow architecture rules strictly** - Never violate the layer separation principles
3. **Use the provided coding conventions** - Maintain consistency with existing patterns
4. **Respect the current build phase** - Phase 1 is backend-only, no frontend features yet
5. **Check git branch strategy** - Work on feat/* branches, PR to dev, never commit directly to main

## Known Constraints

- Ollama runs in WSL2. The API endpoint is http://localhost:11434
- Qdrant runs in Docker on port 6333.
- Never suggest cloud APIs or external services — this is a 100% local tool.
- RTX 3060 has 12GB VRAM. Recommended model: Qwen2.5-Coder:7b-instruct-q4_K_M

## Design Decisions

Key architectural choices documented in `docs/decisions/`:
- Tauri over Electron: smaller binary, native file system access, Rust shell
- Qdrant over ChromaDB: better performance, Docker-based, production-ready
- Tree-sitter over regex: grammar-aware, handles nested structures, multi-language
- SQLite over PostgreSQL: zero-config, file-based, perfect for local-first tools

---

**Purpose**: This file serves as a master context for any AI assistant working on The Vault.
**Usage**: Paste this entire file into new chat sessions to provide complete project context.
**Updated**: 2026-03-02 - Phase 1 completion, ready for Phase 2