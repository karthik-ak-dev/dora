"""
API Handlers package.

ARCHITECTURE NOTE: Handler (Controller) Pattern
================================================

Handlers are the HTTP layer of the application. They handle web requests
and responses, but delegate all business logic to the service layer.

RESPONSIBILITY:
- Parse HTTP requests (query params, body, headers)
- Validate request format (via Pydantic schemas)
- Call service methods
- Translate service exceptions to HTTP errors
- Format HTTP responses
- Set HTTP status codes and headers

WHAT BELONGS HERE:
✅ HTTP-specific logic (status codes, headers)
✅ Request parsing and validation
✅ Response formatting
✅ Authentication/authorization checks (via dependencies)
✅ Calling service methods

WHAT DOESN'T BELONG HERE:
❌ Business logic (that's in services)
❌ Database queries (that's in repositories)
❌ Direct repository access (use services)
❌ Password hashing, token generation (use services/utils)
❌ Complex data transformations (that's in services)

DEPENDENCY INJECTION:
All handlers use FastAPI's Depends() for:
- Database sessions
- Services
- Current user
- Pagination parameters

This makes handlers:
- Easy to test (mock dependencies)
- Explicit about what they need
- Following FastAPI best practices

PATTERN:
--------
@router.post("/endpoint")
async def handler(
    request_data: RequestSchema,
    current_user: dict = Depends(get_current_user),
    service: Service = Depends(get_service)
):
    '''Handler docstring explaining what this endpoint does.'''
    try:
        result = service.do_something(request_data, current_user["user_id"])
    except ServiceException as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return ResponseSchema.from_orm(result)

THIN HANDLERS:
Handlers should be THIN - just HTTP plumbing. If a handler has more than
10-15 lines of logic, that logic probably belongs in a service.
"""
