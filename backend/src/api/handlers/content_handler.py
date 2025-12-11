"""
Content Handler

Handles content saving and retrieval endpoints.

ARCHITECTURE:
=============
    Handler → Service → Repository → Model

Handlers should ONLY:
- Parse HTTP requests
- Call service methods
- Format HTTP responses
- Handle HTTP-specific errors

Business logic belongs in the SERVICE layer.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.shared.schemas.content import (
    SaveContentRequest,
    SaveContentResponse,
    UpdateSaveRequest,
    UserContentSaveResponse,
    SharedContentResponse,
    SaveWithContentResponse,
    PaginatedSavesResponse,
    CategoryCountsResponse,
)
from src.shared.services.content_service import ContentService
from src.shared.services.url_service import URLService
from src.shared.models.enums import ContentCategory, ItemStatus
from src.shared.core.exceptions import ConflictError
from src.api.dependencies import CurrentUser
from src.api.dependencies.services import get_content_service


router = APIRouter()


def _build_save_response(save) -> SaveWithContentResponse:
    """Helper to build SaveWithContentResponse from ORM object."""
    return SaveWithContentResponse(
        save=UserContentSaveResponse(
            id=str(save.id),
            user_id=str(save.user_id),
            shared_content_id=str(save.shared_content_id),
            raw_share_text=save.raw_share_text,
            is_favorited=save.is_favorited,
            is_archived=save.is_archived,
            created_at=save.created_at,
        ),
        content=SharedContentResponse(
            id=str(save.shared_content.id),
            url=save.shared_content.url,
            source_platform=save.shared_content.source_platform,
            status=save.shared_content.status,
            title=save.shared_content.title,
            caption=save.shared_content.caption,
            thumbnail_url=save.shared_content.thumbnail_url,
            duration_seconds=save.shared_content.duration_seconds,
            content_category=save.shared_content.content_category,
            topic_main=save.shared_content.topic_main,
            subcategories=save.shared_content.subcategories,
            locations=save.shared_content.locations,
            intent=save.shared_content.intent,
            save_count=save.shared_content.save_count,
            created_at=save.shared_content.created_at,
        ),
    )


@router.post(
    "",
    response_model=SaveContentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_content(
    request: SaveContentRequest,
    current_user: CurrentUser,
    content_service: ContentService = Depends(get_content_service),
):
    """
    Save new content for the authenticated user.

    The URL is normalized and deduplicated. If the content already exists
    globally, it's reused. If the user already saved it, returns an error.
    """
    # Validate and process URL
    normalized_url, url_hash, platform = URLService.validate_and_process(request.url)

    # Save content via service
    try:
        save, content, is_new = await content_service.save_content(
            user_id=UUID(current_user["user_id"]),
            url=normalized_url,
            url_hash=url_hash,
            platform=platform,
            raw_share_text=request.raw_share_text,
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    message = (
        "Content saved successfully. Processing has been queued."
        if is_new
        else "Content already processed and ready to view!"
    )

    return SaveContentResponse(
        save=UserContentSaveResponse(
            id=str(save.id),
            user_id=str(save.user_id),
            shared_content_id=str(save.shared_content_id),
            raw_share_text=save.raw_share_text,
            is_favorited=save.is_favorited,
            is_archived=save.is_archived,
            created_at=save.created_at,
        ),
        content=SharedContentResponse(
            id=str(content.id),
            url=content.url,
            source_platform=content.source_platform,
            status=content.status,
            title=content.title,
            caption=content.caption,
            thumbnail_url=content.thumbnail_url,
            duration_seconds=content.duration_seconds,
            content_category=content.content_category,
            topic_main=content.topic_main,
            subcategories=content.subcategories,
            locations=content.locations,
            intent=content.intent,
            save_count=content.save_count,
            created_at=content.created_at,
        ),
        message=message,
    )


@router.get("", response_model=PaginatedSavesResponse)
async def list_content(
    current_user: CurrentUser,
    content_service: ContentService = Depends(get_content_service),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[ContentCategory] = Query(None, description="Filter by category"),
    status_filter: Optional[ItemStatus] = Query(
        None, alias="status", description="Filter by status"
    ),
    include_archived: bool = Query(False, description="Include archived saves"),
):
    """
    List user's saved content with pagination.

    Supports filtering by:
    - content_category: Filter by category (Travel, Food, Tech, etc.)
    - status: Filter by processing status (PENDING, READY, FAILED)
    - include_archived: Whether to include archived saves
    """
    result = await content_service.get_user_saves(
        user_id=UUID(current_user["user_id"]),
        page=page,
        page_size=page_size,
        category=category,
        status=status_filter,
        include_archived=include_archived,
    )

    return PaginatedSavesResponse(
        items=[_build_save_response(save) for save in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )


@router.get("/categories", response_model=CategoryCountsResponse)
async def get_category_counts(
    current_user: CurrentUser,
    content_service: ContentService = Depends(get_content_service),
):
    """
    Get count of saves per category for the user.

    Returns a breakdown of how many saves exist in each content category.
    """
    counts = await content_service.get_category_counts(UUID(current_user["user_id"]))
    total = sum(counts.values())

    return CategoryCountsResponse(counts=counts, total=total)


@router.get("/{save_id}", response_model=SaveWithContentResponse)
async def get_save(
    save_id: str,
    current_user: CurrentUser,
    content_service: ContentService = Depends(get_content_service),
):
    """
    Get a specific save by ID.

    Returns the save details along with the associated content.
    """
    save = await content_service.get_user_save_by_id(
        user_id=UUID(current_user["user_id"]),
        save_id=UUID(save_id),
    )

    if not save:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Save not found",
        )

    return _build_save_response(save)


@router.patch("/{save_id}", response_model=UserContentSaveResponse)
async def update_save(
    save_id: str,
    request: UpdateSaveRequest,
    current_user: CurrentUser,
    content_service: ContentService = Depends(get_content_service),
):
    """
    Update a save's user-specific fields.

    Can update:
    - raw_share_text: User's personal note
    - is_favorited: Favorite status
    - is_archived: Archived status
    """
    save = await content_service.update_user_save(
        user_id=UUID(current_user["user_id"]),
        save_id=UUID(save_id),
        raw_share_text=request.raw_share_text,
        is_favorited=request.is_favorited,
        is_archived=request.is_archived,
    )

    if not save:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Save not found",
        )

    return UserContentSaveResponse(
        id=str(save.id),
        user_id=str(save.user_id),
        shared_content_id=str(save.shared_content_id),
        raw_share_text=save.raw_share_text,
        is_favorited=save.is_favorited,
        is_archived=save.is_archived,
        created_at=save.created_at,
    )


@router.delete("/{save_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_save(
    save_id: str,
    current_user: CurrentUser,
    content_service: ContentService = Depends(get_content_service),
):
    """
    Delete a save.

    This removes the user's save but keeps the SharedContent
    (other users may have saved it).
    """
    deleted = await content_service.delete_user_save(
        user_id=UUID(current_user["user_id"]),
        save_id=UUID(save_id),
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Save not found",
        )

    return None


@router.post("/{save_id}/favorite", response_model=UserContentSaveResponse)
async def toggle_favorite(
    save_id: str,
    current_user: CurrentUser,
    content_service: ContentService = Depends(get_content_service),
):
    """Toggle favorite status for a save."""
    save = await content_service.get_user_save_by_id(
        user_id=UUID(current_user["user_id"]),
        save_id=UUID(save_id),
    )

    if not save:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Save not found",
        )

    # Toggle favorite
    updated = await content_service.update_user_save(
        user_id=UUID(current_user["user_id"]),
        save_id=UUID(save_id),
        is_favorited=not save.is_favorited,
    )

    return UserContentSaveResponse(
        id=str(updated.id),
        user_id=str(updated.user_id),
        shared_content_id=str(updated.shared_content_id),
        raw_share_text=updated.raw_share_text,
        is_favorited=updated.is_favorited,
        is_archived=updated.is_archived,
        created_at=updated.created_at,
    )


@router.post("/{save_id}/archive", response_model=UserContentSaveResponse)
async def toggle_archive(
    save_id: str,
    current_user: CurrentUser,
    content_service: ContentService = Depends(get_content_service),
):
    """Toggle archive status for a save."""
    save = await content_service.get_user_save_by_id(
        user_id=UUID(current_user["user_id"]),
        save_id=UUID(save_id),
    )

    if not save:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Save not found",
        )

    # Toggle archive
    updated = await content_service.update_user_save(
        user_id=UUID(current_user["user_id"]),
        save_id=UUID(save_id),
        is_archived=not save.is_archived,
    )

    return UserContentSaveResponse(
        id=str(updated.id),
        user_id=str(updated.user_id),
        shared_content_id=str(updated.shared_content_id),
        raw_share_text=updated.raw_share_text,
        is_favorited=updated.is_favorited,
        is_archived=updated.is_archived,
        created_at=updated.created_at,
    )
