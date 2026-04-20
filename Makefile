.PHONY: install format lint test run clean help db-init

# === Quick Start (one command to rule them all) ===
quickstart: install docker-up
	@echo "Waiting for database to be ready..."
	@sleep 8
	@echo "Creating initial migration..."
	cd backend && uv run rachid db migrate -m "initial" || true
	@echo "Applying migrations..."
	cd backend && uv run rachid db upgrade
	@echo "Creating admin user (admin@example.com / admin123)..."
	cd backend && uv run rachid user create --email admin@example.com --password admin123 --superuser 2>/dev/null || true
	@echo ""
	@echo "🚀 Ready! All services running:"
	@echo "   API:      http://localhost:8000"
	@echo "   Docs:     http://localhost:8000/docs"
	@echo "   Frontend: Run 'cd frontend && bun install && bun dev' or 'make docker-frontend'"
	@echo "   Admin:    http://localhost:8000/admin (admin@example.com / admin123)"

# === Setup ===
install:
	uv sync --directory backend --dev
	@if git rev-parse --git-dir > /dev/null 2>&1; then \
		uv run --directory backend pre-commit install; \
	else \
		echo "⚠️  Not a git repository - skipping pre-commit install"; \
		echo "   Run 'git init && make install' to set up pre-commit hooks"; \
	fi
	@echo ""
	@echo "✅ Installation complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  • make docker-db        # Start PostgreSQL"
	@echo "  • make db-upgrade       # Apply migrations"
	@echo "  • make run              # Start development server"
	@echo ""
	@echo "Note: backend/.env is pre-configured for development"

# === Code Quality ===
format:
	uv run --directory backend ruff format app tests cli
	uv run --directory backend ruff check app tests cli --fix

lint:
	uv run --directory backend ruff check app tests cli
	uv run --directory backend ruff format app tests cli --check
	uv run --directory backend ty check

# === Testing ===
test:
	uv run --directory backend pytest tests/ -v

test-cov:
	uv run --directory backend pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

# === Database ===
db-init: docker-db
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 8
	cd backend && uv run rachid db migrate -m "initial" || true
	cd backend && uv run rachid db upgrade
	@echo ""
	@echo "✅ Database initialized!"

db-migrate:
	@read -p "Migration message: " msg; \
	uv run --directory backend rachid db migrate -m "$$msg"

db-upgrade:
	uv run --directory backend rachid db upgrade

db-downgrade:
	uv run --directory backend rachid db downgrade

db-current:
	uv run --directory backend rachid db current

db-history:
	uv run --directory backend rachid db history

# === Server ===
run:
	uv run --directory backend rachid server run --reload

run-prod:
	uv run --directory backend rachid server run --host 0.0.0.0 --port 8000

routes:
	uv run --directory backend rachid server routes

# === Users ===
create-admin:
	@echo "Creating admin user..."
	uv run --directory backend rachid user create-admin

user-create:
	uv run --directory backend rachid user create

user-list:
	uv run --directory backend rachid user list

# === Celery ===
celery-worker:
	uv run --directory backend rachid celery worker

celery-beat:
	uv run --directory backend rachid celery beat

celery-flower:
	uv run --directory backend rachid celery flower
	@echo ""
	@echo "✅ Flower started at http://localhost:5555"

# === Docker: Backend (Development) ===
docker-up:
	docker-compose build app
	docker-compose up -d
	@echo ""
	@echo "✅ Backend services started!"
	@echo "   API: http://localhost:8000"
	@echo "   Docs: http://localhost:8000/docs"
	@echo "   Flower: http://localhost:5555"
	@echo "   PostgreSQL: localhost:5433"
	@echo "   Redis: localhost:6379"

docker-down:
	docker-compose down
	docker-compose -f docker-compose.frontend.yml down 2>/dev/null || true

docker-logs:
	docker-compose logs -f

docker-build:
	docker-compose build

docker-shell:
	docker-compose exec app /bin/bash

# === Docker: Frontend (Development) ===
docker-frontend:
	docker-compose -f docker-compose.frontend.yml up -d
	@echo ""
	@echo "✅ Frontend started!"
	@echo "   URL: http://localhost:3000"
	@echo ""
	@echo "Note: Backend must be running (make docker-up)"

docker-frontend-down:
	docker-compose -f docker-compose.frontend.yml down

docker-frontend-logs:
	docker-compose -f docker-compose.frontend.yml logs -f

docker-frontend-build:
	docker-compose -f docker-compose.frontend.yml build

# === Docker: Production (with Traefik) ===
docker-prod:
	docker-compose -f docker-compose.prod.yml up -d
	@echo ""
	@echo "✅ Production services started with Traefik!"
	@echo ""
	@echo "Endpoints (replace DOMAIN with your domain):"
	@echo "   Frontend: https://$$DOMAIN"
	@echo "   API: https://api.$$DOMAIN"
	@echo "   Flower: https://flower.$$DOMAIN"
	@echo "   Traefik: https://traefik.$$DOMAIN"

docker-prod-down:
	docker-compose -f docker-compose.prod.yml down

docker-prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f

docker-prod-build:
	docker-compose -f docker-compose.prod.yml build

# === Docker: Individual Services ===
docker-db:
	docker-compose up -d db
	@echo ""
	@echo "✅ PostgreSQL started on port 5433"
	@echo "   Connection: postgresql://postgres:postgres@localhost:5433/rachid"

docker-db-stop:
	docker-compose stop db

docker-redis:
	docker-compose up -d redis
	@echo ""
	@echo "✅ Redis started on port 6379"

docker-redis-stop:
	docker-compose stop redis

# === Vercel (Frontend Deployment) ===
vercel-deploy:
	cd frontend && npx vercel --prod
	@echo ""
	@echo "✅ Frontend deployed to Vercel!"
	@echo "   Set environment variables in Vercel dashboard:"
	@echo "   BACKEND_URL=https://api.your-domain.com"
	@echo "   BACKEND_WS_URL=wss://api.your-domain.com"
	@echo "   NEXT_PUBLIC_AUTH_ENABLED=true"
	@echo "   NEXT_PUBLIC_RAG_ENABLED=true"

# === Cleanup ===
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ty_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml

# === Help ===
help:
	@echo ""
	@echo "rachid - Available Commands"
	@echo "======================================"
	@echo ""
	@echo "Quick Start:"
	@echo "  make quickstart    Install + start all services + setup DB"
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install dependencies + pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  make run           Start dev server (with hot reload)"
	@echo "  make test          Run tests"
	@echo "  make lint          Check code quality"
	@echo "  make format        Auto-format code"
	@echo ""
	@echo "Database:"
	@echo "  make db-init       Initialize database (start + migrate)"
	@echo "  make db-migrate    Create new migration"
	@echo "  make db-upgrade    Apply migrations"
	@echo "  make db-downgrade  Rollback last migration"
	@echo "  make db-current    Show current migration"
	@echo ""
	@echo "Users:"
	@echo "  make create-admin  Create admin user (for SQLAdmin access)"
	@echo "  make user-create   Create new user (interactive)"
	@echo "  make user-list     List all users"
	@echo ""
	@echo "RAG:"
	@echo "  uv run rachid rag-ingest <path> -c <collection>  Ingest files"
	@echo "  uv run rachid rag-search <query> -c <collection>  Search"
	@echo "  uv run rachid rag-collections                     List collections"
	@echo "  uv run rachid rag-sources                         List sync sources"
	@echo "  uv run rachid rag-source-add                      Add sync source"
	@echo "  uv run rachid rag-source-sync <id>                Trigger sync"
	@echo ""
	@echo "Celery:"
	@echo "  make celery-worker  Start Celery worker"
	@echo "  make celery-beat    Start Celery beat scheduler"
	@echo "  make celery-flower  Start Flower monitoring UI"
	@echo ""
	@echo "Docker (Development):"
	@echo "  make docker-up            Start backend services"
	@echo "  make docker-down          Stop all services"
	@echo "  make docker-logs          View backend logs"
	@echo "  make docker-build         Build backend images"
	@echo "  make docker-frontend      Start frontend (separate)"
	@echo "  make docker-frontend-down Stop frontend"
	@echo "  make docker-db            Start only PostgreSQL"
	@echo "  make docker-redis         Start only Redis"
	@echo ""
	@echo "Docker (Production with Traefik):"
	@echo "  make docker-prod          Start production stack"
	@echo "  make docker-prod-down     Stop production stack"
	@echo "  make docker-prod-logs     View production logs"
	@echo ""
	@echo "Other:"
	@echo "  make routes        Show all API routes"
	@echo "  make clean         Clean cache files"
	@echo ""
