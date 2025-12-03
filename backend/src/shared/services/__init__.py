"""
Service layer package.

ARCHITECTURE NOTE: Service Layer Pattern
=========================================

The service layer sits between handlers (API/Worker) and repositories (data access).

RESPONSIBILITY:
- Business logic and orchestration
- Transaction management
- Validation of business rules
- Coordination of multiple repositories
- Integration with external services (via adapters)

WHAT BELONGS HERE:
✅ Business logic (e.g., "user can't save same content twice")
✅ Multi-step operations (e.g., "create user + send welcome email")
✅ Data transformation for business needs
✅ Calling multiple repositories
✅ Using utility functions (security, validation)

WHAT DOESN'T BELONG HERE:
❌ HTTP request/response handling (that's in handlers)
❌ Database queries (that's in repositories)
❌ Direct database access (use repositories)
❌ Framework-specific code (FastAPI, etc.)

DEPENDENCY FLOW:
Handler/Processor → Service → Repository → Model
                  ↘ Adapters ↗

REUSABILITY:
Services are shared between:
- API handlers (HTTP endpoints)
- Worker processors (background jobs)
- CLI scripts
- Tests

This ensures business logic is written once and reused everywhere.

EXAMPLE:
--------
# ❌ BAD - Business logic in handler
@router.post("/register")
async def register(data, db):
    if user_repo.email_exists(data.email):  # ← Business logic
        raise HTTPException(...)
    password_hash = hash_password(data.password)  # ← Business logic
    user = user_repo.create(...)
    return user

# ✅ GOOD - Business logic in service
@router.post("/register")
async def register(data, auth_service):
    user, token = auth_service.register_user(data.email, data.password)
    return {"user": user, "token": token}
"""
