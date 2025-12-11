"""
Cluster Handler

Handles AI-generated content cluster endpoints.

ARCHITECTURE:
=============
    Handler → Service → Repository → Model

Handlers should ONLY:
- Parse HTTP requests
- Call service methods
- Format HTTP responses
- Handle HTTP-specific errors
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.shared.schemas.cluster import (
    ClusterResponse,
    ClusterWithItemsResponse,
    ClusterListResponse,
)
from src.shared.services.cluster_service import ClusterService
from src.shared.models.enums import ContentCategory
from src.api.dependencies import CurrentUser
from src.api.dependencies.services import get_cluster_service


router = APIRouter()


@router.get("", response_model=ClusterListResponse)
async def list_clusters(
    current_user: CurrentUser,
    cluster_service: ClusterService = Depends(get_cluster_service),
    category: Optional[ContentCategory] = Query(None, description="Filter by category"),
):
    """
    List user's content clusters.

    Optionally filter by content category.

    Returns:
        List of clusters with item counts
    """
    if category:
        clusters = await cluster_service.get_user_clusters_by_category(
            user_id=UUID(current_user["user_id"]),
            content_category=category,
        )
        # For category filter, we need to get counts separately
        cluster_responses = []
        for cluster in clusters:
            result = await cluster_service.get_cluster_with_items(
                cluster_id=cluster.id,
                user_id=UUID(current_user["user_id"]),
            )
            cluster_responses.append(
                ClusterResponse(
                    id=str(cluster.id),
                    content_category=cluster.content_category,
                    label=cluster.label,
                    short_description=cluster.short_description,
                    item_count=result["item_count"] if result else 0,
                    created_at=cluster.created_at,
                    updated_at=cluster.updated_at,
                )
            )
    else:
        clusters_with_counts = await cluster_service.get_user_clusters_with_counts(
            user_id=UUID(current_user["user_id"]),
        )
        cluster_responses = [
            ClusterResponse(
                id=str(item["cluster"].id),
                content_category=item["cluster"].content_category,
                label=item["cluster"].label,
                short_description=item["cluster"].short_description,
                item_count=item["item_count"],
                created_at=item["cluster"].created_at,
                updated_at=item["cluster"].updated_at,
            )
            for item in clusters_with_counts
        ]

    return ClusterListResponse(
        clusters=cluster_responses,
        total=len(cluster_responses),
    )


@router.get("/{cluster_id}", response_model=ClusterWithItemsResponse)
async def get_cluster(
    cluster_id: str,
    current_user: CurrentUser,
    cluster_service: ClusterService = Depends(get_cluster_service),
):
    """
    Get a specific cluster with all its items.

    Returns:
        Cluster details with list of items
    """
    result = await cluster_service.get_cluster_with_items(
        cluster_id=UUID(cluster_id),
        user_id=UUID(current_user["user_id"]),
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found",
        )

    cluster = result["cluster"]
    items = result["items"]

    return ClusterWithItemsResponse(
        cluster=ClusterResponse(
            id=str(cluster.id),
            content_category=cluster.content_category,
            label=cluster.label,
            short_description=cluster.short_description,
            item_count=result["item_count"],
            created_at=cluster.created_at,
            updated_at=cluster.updated_at,
        ),
        items=[
            {
                "id": str(item.id),
                "shared_content_id": str(item.shared_content_id),
                "raw_share_text": item.raw_share_text,
                "is_favorited": item.is_favorited,
                "created_at": item.created_at,
                "content": {
                    "id": str(item.shared_content.id),
                    "url": item.shared_content.url,
                    "title": item.shared_content.title,
                    "thumbnail_url": item.shared_content.thumbnail_url,
                    "source_platform": item.shared_content.source_platform,
                }
                if item.shared_content
                else None,
            }
            for item in items
        ],
    )


@router.delete("/{cluster_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cluster(
    cluster_id: str,
    current_user: CurrentUser,
    cluster_service: ClusterService = Depends(get_cluster_service),
):
    """
    Delete a cluster.

    Note: This only deletes the cluster, not the content saves within it.
    The saves remain and can be re-clustered.
    """
    deleted = await cluster_service.delete_cluster(
        cluster_id=UUID(cluster_id),
        user_id=UUID(current_user["user_id"]),
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found",
        )

    return None
