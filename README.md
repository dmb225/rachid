# Rachid

Your wise conpanion

## Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI + Pydantic v2 |
| **Database** | PostgreSQL (async) |
| **Auth** | JWT + API Key + refresh tokens |
| **Cache** | Redis |
| **AI Framework** | pydantic_ai (openrouter) |
| **RAG** | pgvector vector store |
| **Tasks** | celery |
| **Frontend** | Next.js 15 + React 19 + Tailwind v4 |

## Quick Start

```bash
# Install dependencies
make install
# One-command setup (Docker required)
make quickstart
```
This will:
1. Install Python dependencies
2. Start all Docker services (database, Redis, vector store, etc.)
3. Run database migrations
4. Create an admin user (`admin@example.com` / `admin123`)

**Access:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Admin: http://localhost:8000/admin
- Frontend: http://localhost:3000 (run `cd frontend && bun dev`)

## Manual Setup

If you prefer to set up step by step:

```bash
# 1. Install dependencies
make install
# 2. Start database
make docker-db
# 3. Create and apply migrations
make db-migrate    # Enter: "Initial migration"
make db-upgrade

# 4. Create admin user
make create-admin

# 5. Start backend
make run
# 6. Start frontend (new terminal)
cd frontend && bun install && bun dev
```

## Commands

Run `make help` for all available commands. Key ones:

| Command | Description |
|---------|-------------|
| `make run` | Start dev server with hot reload |
| `make test` | Run tests |
| `make lint` | Check code quality |
| `make format` | Auto-format code |
| `make db-migrate` | Create new migration |
| `make db-upgrade` | Apply migrations |
| `make create-admin` | Create admin user |
| `make quickstart` | Full setup (install + docker + db + admin) |
| `make docker-up` | Start all Docker services |
| `make docker-down` | Stop all services |


## AI Agent

Using **pydantic_ai** with **openrouter** provider.
Chat with the agent at http://localhost:3000/chat

### Customize

- **System prompt:** `app/agents/prompts.py`
- **Add tools:** See `docs/howto/add-agent-tool.md`
- **Agent config:** `.env` → `AI_MODEL`, `AI_TEMPERATURE`

## RAG (Knowledge Base)

Using **pgvector** as vector store.

### Ingest documents

```bash
# Local files
uv run rachid rag-ingest /path/to/docs/ --collection documents --recursive
# Google Drive
uv run rachid rag-sync-gdrive --collection documents --folder-id <id>
# S3/MinIO
uv run rachid rag-sync-s3 --collection documents --prefix docs/
```

### Search

```bash
uv run rachid rag-search "your query" --collection documents
```

### Manage collections

```bash
uv run rachid rag-collections   # List all
uv run rachid rag-stats          # Show stats
uv run rachid rag-drop <name>    # Delete collection
```

### Sync sources

Sync sources let you configure recurring document ingestion from external
systems (Google Drive, S3, etc.) via the API or CLI.

```bash
uv run rachid cmd rag-sources          # List configured sources
uv run rachid cmd rag-source-add       # Add a new source
uv run rachid cmd rag-source-sync      # Trigger sync for a source
uv run rachid cmd rag-source-remove    # Remove a source
```

See `docs/howto/add-sync-connector.md` for how to add custom connectors.

## Project Structure

```
backend/app/
├── api/routes/v1/        # API endpoints
├── core/config.py        # Settings (from .env)
├── services/             # Business logic
├── repositories/         # Data access
├── schemas/              # Pydantic models
├── db/models/            # Database models
├── agents/               # AI agents & tools
├── rag/                  # RAG pipeline (embeddings, vector store, ingestion)
│   └── connectors/       # Sync source connectors
├── commands/             # CLI commands (auto-discovered)
└── worker/               # Background tasks
```

## Guides

| Guide | Description |
|-------|-------------|
| `docs/howto/add-api-endpoint.md` | Add a new API endpoint |
| `docs/howto/add-agent-tool.md` | Create a new agent tool |
| `docs/howto/customize-agent-prompt.md` | Customize agent behavior |
| `docs/howto/add-background-task.md` | Add background tasks |
| `docs/howto/add-rag-source.md` | Add a new RAG document source |
| `docs/howto/add-sync-connector.md` | Create a new sync connector |

## Environment Variables

All config is in `backend/.env`. Key variables:

```bash
POSTGRES_HOST=localhost
POSTGRES_PASSWORD=postgres
RAG_CHUNKING_STRATEGY=recursive  # recursive, markdown, fixed
RAG_HYBRID_SEARCH=false
```

See `backend/.env.example` for all available variables.

## Deployment

### Frontend (Vercel)

```bash
cd frontend
npx vercel --prod
```

Set environment variables in Vercel dashboard:
- `BACKEND_URL` = your backend URL
- `BACKEND_WS_URL` = your backend WebSocket URL
- `NEXT_PUBLIC_AUTH_ENABLED` = `true`
- `NEXT_PUBLIC_RAG_ENABLED` = `true`

### Backend (Docker)

```bash
make docker-prod
```

---

*Project based on [Full-Stack AI Agent Template](https://github.com/vstorm-co/full-stack-ai-agent-template) v0.2.4*
