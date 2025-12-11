# Dora API - Run & Test Guide

Complete step-by-step guide to run and test the Dora API locally.

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Postman (for API testing)

---

## Quick Start (5 minutes)

### Step 1: Start Infrastructure Services

```bash
cd backend

# Start PostgreSQL, Redis, and Qdrant
docker-compose up -d postgres redis qdrant

# Verify services are running
docker-compose ps
```

Expected output:
```
NAME                STATUS              PORTS
dora-postgres       running (healthy)   0.0.0.0:5432->5432/tcp
dora-redis          running             0.0.0.0:6379->6379/tcp
dora-qdrant         running             0.0.0.0:6333->6333/tcp
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate it
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements/api.txt
```

### Step 3: Configure Environment

```bash
# Create .env file from example
cp .env.example .env
```

Edit `.env` with these values for local development:
```env
# Application
APP_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database (asyncpg driver required)
DATABASE_URL=postgresql+asyncpg://dora:dora@localhost:5432/dora

# Security (change in production!)
SECRET_KEY=local-dev-secret-key-change-in-production

# Optional services
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
```

### Step 4: Run Database Migrations

```bash
# Apply all migrations
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial schema
```

### Step 5: Start the API Server

```bash
# Development mode with auto-reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Application startup complete.
```

### Step 6: Verify API is Running

Open in browser or use curl:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "dora",
  "version": "1.0.0"
}
```

---

## API Documentation

When `DEBUG=true`, interactive API docs are available:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Testing with Postman

### Import Collection

1. Open Postman
2. Click **Import**
3. Select files from `src/api/postman/`:
   - `Dora_API.postman_collection.json`
   - `Dora_Local.postman_environment.json`
4. Select **Dora - Local Development** environment

### Test Flow

#### 1. Health Check
- Request: `GET /health`
- Expected: `200 OK` with status "healthy"

#### 2. Register User
- Request: `POST /auth/register`
- Body:
  ```json
  {
    "email": "test@example.com",
    "password": "password123"
  }
  ```
- Expected: `201 Created` with user data and JWT token
- **Note**: Token is auto-saved to collection variables

#### 3. Login (if already registered)
- Request: `POST /auth/login`
- Body:
  ```json
  {
    "email": "test@example.com",
    "password": "password123"
  }
  ```
- Expected: `200 OK` with JWT token

#### 4. Save Content
- Request: `POST /items`
- Headers: `Authorization: Bearer {{access_token}}`
- Body:
  ```json
  {
    "url": "https://www.instagram.com/p/ABC123/",
    "raw_share_text": "Check this out!"
  }
  ```
- Expected: `201 Created` with save details
- **Note**: Save ID is auto-stored for subsequent requests

#### 5. List Content
- Request: `GET /items`
- Headers: `Authorization: Bearer {{access_token}}`
- Expected: `200 OK` with paginated list

#### 6. Get Category Counts
- Request: `GET /items/categories`
- Headers: `Authorization: Bearer {{access_token}}`
- Expected: `200 OK` with category breakdown

---

## API Endpoints Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login and get token |

### Content (Items)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/items` | Save new content |
| GET | `/items` | List saves (paginated) |
| GET | `/items/categories` | Get category counts |
| GET | `/items/{id}` | Get single save |
| PATCH | `/items/{id}` | Update save |
| DELETE | `/items/{id}` | Delete save |
| POST | `/items/{id}/favorite` | Toggle favorite |
| POST | `/items/{id}/archive` | Toggle archive |

### Clusters
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/clusters` | List clusters |
| GET | `/clusters/{id}` | Get cluster with items |
| DELETE | `/clusters/{id}` | Delete cluster |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/ready` | Readiness probe |
| GET | `/live` | Liveness probe |

---

## Common Issues & Solutions

### Database Connection Error
```
sqlalchemy.exc.OperationalError: could not connect to server
```
**Solution**: Ensure PostgreSQL is running:
```bash
docker-compose up -d postgres
docker-compose logs postgres  # Check for errors
```

### Migration Error
```
alembic.util.exc.CommandError: Can't locate revision
```
**Solution**: Reset migrations:
```bash
# Drop and recreate database
docker-compose down -v
docker-compose up -d postgres
alembic upgrade head
```

### Port Already in Use
```
OSError: [Errno 48] Address already in use
```
**Solution**: Kill the process or use a different port:
```bash
# Find process using port 8000
lsof -i :8000
kill -9 <PID>

# Or use different port
uvicorn src.api.main:app --port 8001
```

### JWT Token Expired
```
{"detail": "Token has expired"}
```
**Solution**: Login again to get a new token.

---

## Running Tests

```bash
# Install test dependencies
pip install -r requirements/dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_auth.py -v
```

---

## Docker Compose Commands

```bash
# Start all services
docker-compose up -d

# Start only infrastructure (for local API development)
docker-compose up -d postgres redis qdrant

# View logs
docker-compose logs -f api
docker-compose logs -f postgres

# Stop all services
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v

# Rebuild images
docker-compose build --no-cache
```

---

## Development Tips

### Auto-reload
The `--reload` flag watches for file changes:
```bash
uvicorn src.api.main:app --reload
```

### Debug Mode
Set `DEBUG=true` in `.env` to:
- Enable Swagger/ReDoc docs
- Enable SQL query logging
- Show detailed error messages

### Database Shell
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U dora -d dora

# Common queries
\dt                    # List tables
\d users              # Describe users table
SELECT * FROM users;  # Query users
```

### View API Logs
```bash
# If running with uvicorn directly
# Logs appear in terminal

# If running with Docker
docker-compose logs -f api
```
