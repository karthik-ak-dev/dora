"""
Content handler.
Handles content saving and retrieval.

ARCHITECTURE NOTE:
This handler follows the proper layered architecture:
  Handler → Service → Repository → Model

Handlers should ONLY:
- Parse HTTP requests
- Call service methods
- Format HTTP responses
- Handle HTTP-specific errors

Business logic belongs in the SERVICE layer.

DEPENDENCY INJECTION:
Services are injected via FastAPI's Depends() mechanism for:
- Better testability (easy to mock services)
- Explicit dependencies
- FastAPI best practices
"""
from fastapi import APIRouter, Depends, HTTPException, status

from ...shared.schemas.content import SaveContentRequest, SaveContentResponse
from ...shared.schemas.content import UserContentSaveResponse, SharedContentResponse
from ...shared.services.content_service import ContentService
from ...shared.services.url_service import URLService
from ..dependencies.services import get_content_service
from ..dependencies.auth import get_current_user

router = APIRouter()


@router.post("", response_model=SaveContentResponse, status_code=status.HTTP_201_CREATED)
async def save_content(
    request: SaveContentRequest,
    current_user: dict = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service)
):
    """
    Save new content for the authenticated user.
    
    The URL is normalized and deduplicated. If the content already exists
    globally, it's reused. If the user already saved it, returns an error.
    """
    # Validate and process URL (stateless utility, no injection needed)
    normalized_url, url_hash, platform = URLService.validate_and_process(request.url)
    
    # Save content via service
    try:
        save, content, is_new = content_service.save_content(
            user_id=current_user["user_id"],
            url=normalized_url,
            url_hash=url_hash,
            raw_share_text=request.raw_share_text
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # TODO: Enqueue processing job if is_new
    
    message = (
        "Content saved successfully. Processing has been queued." if is_new
        else "Content already processed and ready to view!"
    )
    
    return SaveContentResponse(
        save=UserContentSaveResponse.from_orm(save),
        content=SharedContentResponse.from_orm(content),
        message=message
    )


@router.get("")
async def list_content(
    current_user: dict = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service)
):
    """
    List user's saved content.
    
    TODO: Implement with filtering, sorting, and pagination.
    """
    # TODO: Implement list with filtering and pagination
    return {"items": [], "total": 0}
