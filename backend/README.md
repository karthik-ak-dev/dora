# Dora Backend

AI-Powered Second Brain for Content.

## Project Structure

```
backend/
├── src/
│   ├── shared/              # Shared components (API & Worker)
│   │   ├── core/           # Logging, exceptions
│   │   ├── db/             # Async database session management
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── repositories/   # Data access layer (async)
│   │   ├── services/       # Business logic (async)
│   │   ├── schemas/        # Pydantic request/response models
│   │   ├── adapters/       # External service integrations
│   │   └── utils/          # Security, constants
│   ├── api/                # FastAPI application
│   │   ├── handlers/       # Route handlers
│   │   ├── middleware/     # Error handling middleware
│   │   └── dependencies/   # FastAPI dependencies (DI)
│   ├── worker/             # Background job processing
│   │   ├── processors/     # Job processors
│   │   ├── pipelines/      # Multi-stage pipelines
│   │   └── scrapers/       # Platform-specific scrapers
│   └── config/             # Configuration (settings)
├── tests/                  # Test suite
├── scripts/                # Utility scripts
├── alembic/                # Database migrations
└── requirements/           # Dependency management
```

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis (optional, for caching)

### 1. Create Virtual Environment

```bash
cd backend

# Create venv
python3.11 -m venv .venv

# Activate venv
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows
```

### 2. Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# For API development
pip install -r requirements/api.txt

# For worker development
pip install -r requirements/worker.txt

# For development (includes testing tools)
pip install -r requirements/dev.txt

# Install all (API + Worker + Dev)
pip install -r requirements/base.txt -r requirements/worker.txt -r requirements/dev.txt
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your configuration
# Required: DATABASE_URL, SECRET_KEY
```

Example `.env`:
```env
# Application
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

# Database (use asyncpg driver)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dora

# Security
SECRET_KEY=your-secret-key-change-in-production

# OpenAI (for worker)
OPENAI_API_KEY=sk-your-key

# Qdrant (for worker)
QDRANT_URL=http://localhost:6333
```

### 4. Start PostgreSQL (Docker)

```bash
# Start PostgreSQL with Docker
docker run -d \
  --name dora-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=dora \
  -p 5432:5432 \
  postgres:14

# Or use docker-compose
docker-compose up -d postgres
```

### 5. Run Database Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create new migration after model changes
alembic revision --autogenerate -m "description"
```

### 6. Run the API Server

```bash
# Development mode with auto-reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

API Endpoints:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs (only in DEBUG mode)
- Health: http://localhost:8000/health

### 7. Run the Worker (optional)

```bash
python -m src.worker.main
```

## Development

### Code Quality

```bash
# Format code with Black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Lint with Ruff
ruff check src/

# Type checking with mypy
mypy src/
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/unit/test_auth.py -v
```

## Architecture

### Layer Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    API / Worker Entry Points                 │
├─────────────────────────────────────────────────────────────┤
│   Handlers/Processors (HTTP parsing, response formatting)   │
├─────────────────────────────────────────────────────────────┤
│              Services (Business Logic)                       │
├─────────────────────────────────────────────────────────────┤
│         Repositories (Data Access, Async SQLAlchemy)        │
├─────────────────────────────────────────────────────────────┤
│                 Models (ORM Entities)                        │
└─────────────────────────────────────────────────────────────┘
```

### Key Patterns

| Component | Pattern | Location |
|-----------|---------|----------|
| Database | Async SQLAlchemy 2.0 | `shared/db/session.py` |
| Models | `Mapped[]` + `mapped_column()` | `shared/models/` |
| Repositories | Generic async CRUD | `shared/repositories/base.py` |
| Services | Business logic + coordination | `shared/services/` |
| Logging | structlog | `shared/core/logging.py` |
| Exceptions | Hierarchy with `to_dict()` | `shared/core/exceptions.py` |
| Dependencies | Type aliases (`DbSession`, `CurrentUser`) | `api/dependencies/` |

### Database Session Flow
```
Request → get_db() dependency → AsyncSession → Repository → Database
                                     ↓
                              Auto-commit on success
                              Auto-rollback on error
                              Auto-close on finish
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/production) | development |
| `DEBUG` | Enable debug mode | false |
| `DATABASE_URL` | PostgreSQL URL (asyncpg) | required |
| `SECRET_KEY` | JWT signing key | required |
| `LOG_LEVEL` | Logging level | INFO |
| `CORS_ORIGINS` | Allowed CORS origins | ["http://localhost:3000"] |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `QDRANT_URL` | Qdrant vector DB URL | http://localhost:6333 |

## Database Migrations

```bash
# Create migration after model changes
alembic revision --autogenerate -m "add user roles"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Show migration history
alembic history
```

## Docker

### Build Images

```bash
# Build API image
docker build -f Dockerfile.api -t dora-api .

# Build Worker image
docker build -f Dockerfile.worker -t dora-worker .
```

### Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop all
docker-compose down
```

## License

MIT
