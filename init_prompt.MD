# Project: The Vault — Session Context

You are helping me build **The Vault**, a local-first, AI-powered code 
archaeology desktop application. Read this entire document before doing 
anything else.

---

## What It Is

A personal developer tool that:
- Recursively scans project directories across multiple drives
- Parses every code file and extracts all symbols (classes, methods, 
  fields, enums, interfaces, etc.) using Tree-sitter
- Sends each symbol to a local Ollama instance (WSL2, RTX 3060 12GB) 
  for AI documentation — once, stored permanently
- Stores everything in SQLite (metadata) + Qdrant (vector embeddings) 
  + .vault/*.json files (portable AI doc cache per project)
- Provides a desktop UI to browse projects, read AI-generated docs 
  per symbol, and run semantic search across the entire codebase history

The core value proposition: pay the AI cost once, query forever. 
No cloud. No subscriptions. 100% local.

---

## Tech Stack

| Layer      | Technology                                      |
|------------|-------------------------------------------------|
| Backend    | FastAPI, Python 3.11+, SQLAlchemy, SQLite       |
| AI         | Ollama (WSL2) — Qwen2.5-Coder:7b-instruct-q4   |
| Vectors    | Qdrant (Docker, port 6333) + nomic-embed-text   |
| Parser     | tree-sitter (Python bindings) — C#, Java, Py, JS, RenPy |
| Frontend   | Tauri v2 + React 18 + TypeScript 5 + Tailwind  |
| Cache      | .vault/symbols/*.json inside each project root  |

---

## Architecture — Layer Rules (Never Violate)

1. **Parser layer** (tree-sitter) NEVER calls Ollama. Separate concerns.
2. **Ollama** is called ONLY from backend/vault/ai/ — nowhere else.
3. **FastAPI routes** are thin — logic lives in service modules, not routes.
4. **Frontend** NEVER reads files directly — all data through the API.
5. **Qdrant** is accessed ONLY through storage/vector_store.py.
6. The .vault/ folder in each project is append-only. Never delete user files.

---

## Repository Structure
```
the-vault/
├── AGENTS.md                  # Master AI context (this document, committed)
├── .cursorrules               # Cursor overrides
├── .windsurfrules             # Windsurf overrides
├── backend/vault/
│   ├── crawler/               # File watcher + project scanner
│   ├── parser/                # Tree-sitter symbol extraction
│   ├── ai/                    # Ollama client + doc generation queue
│   ├── storage/               # SQLAlchemy models, Qdrant wrapper, JSON cache
│   └── api/                   # FastAPI route handlers
├── frontend/src/
│   ├── pages/                 # Registry, ProjectDetail, Search, Timeline
│   └── components/            # ProjectCard, CodeViewer, SymbolDocPanel
├── docs/
│   └── decisions/             # ADRs — one file per architectural decision
└── .github/workflows/         # ci.yml + release.yml
```

---

## Data Models (abbreviated)

**Project** — id, name, path, type (Unity|Java|Python|Node|RenPy), 
loc_total, last_modified, health_score, summary_ai, patterns_detected, 
abandonment_reason, index_status, git_has, refactor_seed candidates

**Symbol** — id, project_id, file_path, symbol_type (Class|Method|Field|
Enum|Interface|Property|Constructor), name, qualified_name, signature, 
raw_code, doc_summary, doc_purpose, doc_pattern, doc_reuse (HIGH|MEDIUM|
LOW|PROJECT_SPECIFIC), doc_example, doc_notes, has_todo, embedding_id, 
content_hash, refactor_seed (bool), refactor_score, pattern_group

---

## Features by Priority

### Must Have (build these first, in order)
1. Background crawler — watches root dirs, detects project types by markers
2. Tree-sitter parser — extracts all symbols per language
3. SQLite storage — Project and Symbol models
4. Ollama doc queue — generates JSON documentation per symbol, cached
5. Qdrant integration — embeds summaries, enables semantic search
6. Frontend registry — project grid with health indicators
7. Code viewer — syntax highlighted with AI docs panel per symbol

### Nice to Have (Phase 5)
- Development timeline (file timestamp-based history)
- Cross-project pattern map (visual graph)
- TODO/FIXME global tracker
- Code snippet pinboard
- Abandonment diagnosis per project
- Git history integration
- **Knowledge Graph Export** — .vault/graph.json mapping patterns 
  across projects. YARVIS ingests this as a static artifact.
- **Refactor Potential Scoring** — second-pass Ollama prompt ranks 
  all symbols sharing a pattern; best one flagged as refactor_seed=true 

### Dream (depends on YARVIS plugin system)
- Per-project bounded RAG chat
- Asset Package Assembler (extract + package a system with one click)
- "Port This To…" button (AI translates a class to another language)
- **YARVIS CLI Recall** — yarvis recall "best inventory system I wrote" 
  calls POST /api/search, gets ranked results from The Vault

---

## Git & Workflow Conventions

**Branching:** main (protected) ← dev (protected) ← feat/* fix/* chore/*  
**Commits:** Conventional Commits — feat(parser): add C# class extractor  
**Scopes:** crawler, parser, ai, storage, api, ui, search, graph, refactor  
**Tags:** semver — v0.1.0-alpha (Phase 1), v0.2.0-alpha (Phase 2), 
          v0.3.0-beta (Phase 3), v0.4.0-beta (Phase 4), v1.0.0 (Phase 5)  

**ADRs live in** docs/decisions/ — one file per major tech decision.  
Written BEFORE the code that implements the decision.

---

## Coding Conventions

**Python:**
- Type hints everywhere. No Any without a comment.
- Async/await for all I/O.
- Pydantic v2 for schemas. Google-style docstrings.
- Logging via structlog, never print().
- Linter: ruff. Type checker: mypy.

**TypeScript:**
- Strict mode. No any without comment.
- All API calls through lib/api.ts only.
- Named exports everywhere except page components.
- No business logic in components — hooks only.

**Forbidden in all files:**
- Cloud SDKs (OpenAI, Anthropic, etc.)
- subprocess with shell=True 
- localStorage in frontend (use Tauri store API)
- Raw fetch() in components

---

## Current Phase

**Phase 1 — Scanner and Parser**  
Goal: Working symbol table in SQLite. No AI, no frontend.  
Active branch: feat/project-scanner  
Focus: backend/vault/crawler/ and backend/vault/parser/  

> UPDATE THIS SECTION at every phase boundary before opening a new branch.

---

## Known Constraints

- Ollama endpoint: http://localhost:11434 (WSL2)
- Qdrant: Docker, port 6333 
- GPU: RTX 3060 12GB — use Q4 quantized models only
- This is 100% local. Never suggest external APIs or cloud services.