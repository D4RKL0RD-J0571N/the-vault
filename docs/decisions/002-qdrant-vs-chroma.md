# ADR-002: Qdrant over ChromaDB for Vector Storage

## Status
Accepted — 2026-03-01

## Context
The Vault needs a local vector store for semantic search across code symbol
embeddings. Two main candidates: Qdrant and ChromaDB. Both run locally.

## Decision
Use Qdrant, deployed via Docker on port 6333.

## Reasons
- Qdrant has a stable REST API that works well from Python and TypeScript.
- Better performance at the scale we expect (50k–500k vectors).
- Docker-based — no Python version conflicts with the backend environment.
- ChromaDB has had API stability issues across minor versions.

## Consequences
- Requires Docker to be running for the full app to work.
- Added docker-compose.yml to manage the Qdrant container.
- All vector operations must go through storage/vector_store.py to allow
  future backend swap without touching business logic.