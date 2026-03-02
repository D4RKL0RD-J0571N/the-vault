# The Vault

A local-first, AI-powered code archaeology desktop application.

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Ollama with Qwen2.5-Coder 7B Instruct (WSL2 recommended)
- RTX 3060 12GB VRAM (or equivalent)

### Development Setup

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd the-vault
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```

2. **Start services**
   ```bash
   # Start Qdrant (Docker)
   docker-compose up -d qdrant
   
   # Start Ollama (WSL2)
   # In WSL2: ollama serve
   # Ensure model is pulled: ollama pull qwen2.5-coder:7b-instruct-q4_K_M
   ```

3. **Run backend**
   ```bash
   cd backend
   python -m uvicorn vault.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Run frontend (Phase 2+)**
   ```bash
   cd frontend
   npm install
   npm run tauri dev
   ```

## Architecture

The Vault follows a strict layered architecture:

- **Parser Layer** (tree-sitter): Fast, deterministic symbol extraction
- **AI Layer** (Ollama): Slow, expensive documentation generation
- **Storage Layer** (SQLite + Qdrant): Metadata and vector search
- **API Layer** (FastAPI): Thin REST endpoints
- **Presentation Layer** (Tauri + React): Desktop application

## Project Status

**Current Phase**: 1 - Scanner and Parser ✅
- Backend symbol extraction: Complete
- Test coverage: 98%
- Ready for Phase 2: Frontend Registry & AI Integration

## Development Rules

This project uses strict development conventions. See:
- `AGENTS.md` - Complete project context for AI assistants
- `.cursorrules` - Cursor-specific configuration  
- `.windsurf/rules` - Windsurf-specific configuration
- `GOVERNANCE.md` - Engineering governance and git workflow

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite, Tree-sitter
- **AI**: Ollama, Qwen2.5-Coder 7B, nomic-embed-text
- **Vectors**: Qdrant (Docker)
- **Frontend**: Tauri v2, React 18, TypeScript 5, Tailwind CSS
- **Testing**: pytest, 98% coverage achieved

## License

MIT License - see LICENSE file for details.

---

**Documentation**: See `docs/` directory for detailed architecture and API reference
**Contributing**: See CONTRIBUTING.md for development guidelines
**Issues**: Use GitHub Issues for bug reports and feature requests
