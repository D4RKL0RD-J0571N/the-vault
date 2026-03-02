# Contributing to The Vault

We welcome contributions! This document outlines how to contribute effectively.

## Development Workflow

1. **Fork and clone** the repository
2. **Create feature branch**: `feat/your-feature-name`
3. **Follow conventions** in `AGENTS.md` and `.cursorrules`/`.windsurf/rules`
4. **Write tests** for all new functionality
5. **Submit Pull Request** to `dev` branch
6. **Ensure CI passes** and coverage remains high

## Code Standards

### Python (Backend)
- Use type hints everywhere (no `Any` without explanation)
- Async/await for all I/O operations
- Pydantic v2 for data validation and API schemas
- Structured logging via `structlog`, never `print()`
- Google-style docstrings for public functions/classes
- Follow existing error handling patterns

### TypeScript (Frontend - Phase 2+)
- Strict mode enabled, no `any` without comment
- All API calls through `lib/api.ts`, never raw `fetch()`
- Component props with interfaces, not inline types
- No business logic in components, hooks only

## Testing

- **Backend**: pytest with high coverage requirement
- **Focus areas**: parser and AI modules especially
- **New features**: Must include tests
- **Coverage**: Maintain 95%+ coverage

## Git Conventions

Follow Conventional Commits:
- Format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `perf`, `test`
- Scopes: `crawler`, `parser`, `ai`, `storage`, `api`, `ui`, `search`, `graph`

## Architecture Rules

Never violate these principles:
1. Parser layer NEVER calls Ollama
2. Ollama called ONLY from `vault/ai/`
3. All file system access through crawler module
4. `.vault/` folder is append-only
5. All Qdrant operations through `storage/vector_store.py`
6. FastAPI routes are thin, business logic in service layer
7. Frontend NEVER reads files directly

## Phase Guidelines

- **Phase 1** (Current): Backend only - scanner, parser, storage, API
- **Phase 2**: Frontend registry + AI integration
- **Phase 3**: Semantic search + knowledge graph
- **Phase 4**: Full features + polish
- **Phase 5**: Production-ready stable release

## Getting Help

- **Architecture decisions**: See `docs/decisions/` ADRs
- **Setup issues**: Check `docs/setup.md`
- **Context**: Always read `AGENTS.md` before starting work

## License

By contributing, you agree to license your code under the MIT License.

---

Thank you for contributing to The Vault! 🚀
