# Dora Backend

## Project Structure

```
backend/
├── src/
│   ├── shared/              # Shared components (used by both API and worker)
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── repositories/   # Data access layer
│   │   ├── services/       # Business logic
│   │   ├── schemas/        # Pydantic request/response models
│   │   ├── adapters/       # External service integrations
│   │   └── utils/          # Utilities and helpers
│   ├── api/                # FastAPI application
│   │   ├── handlers/       # Route handlers (controllers)
│   │   ├── middleware/     # API middleware
│   │   └── dependencies/   # FastAPI dependencies
│   ├── worker/             # Background job processing
│   │   ├── processors/     # Job processors
│   │   ├── pipelines/      # Multi-stage pipelines
│   │   └── scrapers/       # Platform-specific scrapers
│   └── config/             # Configuration management
├── tests/                  # Test suite
├── scripts/                # Utility scripts
├── alembic/                # Database migrations
└── requirements/           # Dependency management
```

## Setup

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 14+

### Installation

1. **Clone the repository**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   # For API development
   pip install -r requirements/api.txt
   
   # For worker development
   pip install -r requirements/worker.txt
   
   # For development (includes testing tools)
   pip install -r requirements/dev.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

6. **Run migrations**
   ```bash
   alembic upgrade head
   ```

## Running Locally

### API Server
```bash
uvicorn src.api.main:app --reload --port 8000
```

API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Worker
```bash
python -m src.worker.main
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py
```

## Code Quality

```bash
# Format code
black src/

# Lint
flake8 src/

# Type checking
mypy src/
```

## Architecture

### Dependency Flow
```
Handlers/Processors → Services → Repositories → Models
                   ↘ Adapters ↗
```

### Shared Components
- **Models**: SQLAlchemy ORM entities
- **Repositories**: CRUD operations and data access
- **Services**: Business logic (reused across API and workers)
- **Schemas**: Pydantic models for validation
- **Adapters**: External service clients (DB, Redis, SQS, OpenAI, Qdrant)
- **Utils**: Common utilities (logging, security, exceptions)

### API Layer
- **Handlers**: FastAPI route handlers
- **Middleware**: Authentication, logging, error handling
- **Dependencies**: Dependency injection (DB session, current user)

### Worker Layer
- **Processors**: Job-specific processing logic
- **Pipelines**: Multi-stage workflows
- **Scrapers**: Platform-specific content extraction

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key
- `OPENAI_API_KEY`: OpenAI API key
- `QDRANT_URL`: Qdrant vector database URL

## License

MIT
