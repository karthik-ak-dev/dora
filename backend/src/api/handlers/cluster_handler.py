"""
Cluster handler.
Handles cluster retrieval.

ARCHITECTURE NOTE:
This handler follows the proper layered architecture:
  Handler → Service → Repository → Model

Handlers should ONLY:
- Parse HTTP requests
- Call service methods
- Format HTTP responses
- Handle HTTP-specific errors

Business logic belongs in the SERVICE layer.

CLUSTERING ARCHITECTURE:
- Clusters are created WITHIN a content_category (not across categories)
- Each cluster groups semantically similar items of the SAME category
- Example: "Cafe Hopping in Indiranagar" cluster contains only Food items
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from ...shared.schemas.cluster import (
    ClusterResponse,
    ClusterWithItemsResponse,
    ClusterItemResponse,
    ClustersByCategoryResponse,
)
from ...shared.services.cluster_service import ClusterService
from ...shared.models.enums import ContentCategory
from ..dependencies.services import get_cluster_service
from ..dependencies.auth import get_current_user

router = APIRouter()


@router.get("", response_model=List[ClusterResponse])
async def list_clusters(
    category: Optional[ContentCategory] = Query(None, description="Filter by content category"),
    current_user: dict = Depends(get_current_user),
    cluster_service: ClusterService = Depends(get_cluster_service),
):
    """
    List user's clusters.

    Returns all clusters belonging to the authenticated user.
    Optionally filter by content_category.

    Each cluster groups items WITHIN a single content_category.
    """
    if category:
        clusters = cluster_service.get_user_clusters_by_category(
            user_id=current_user["user_id"], content_category=category
        )
        return [
            ClusterResponse(
                id=str(c.id),
                user_id=str(c.user_id),
                content_category=c.content_category,
                label=c.label,
                short_description=c.short_description,
                item_count=0,  # Would need separate query
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in clusters
        ]
    else:
        clusters_with_counts = cluster_service.get_user_clusters(current_user["user_id"])
        return [
            ClusterResponse(
                id=str(item["cluster"].id),
                user_id=str(item["cluster"].user_id),
                content_category=item["cluster"].content_category,
                label=item["cluster"].label,
                short_description=item["cluster"].short_description,
                item_count=item["item_count"],
                created_at=item["cluster"].created_at,
                updated_at=item["cluster"].updated_at,
            )
            for item in clusters_with_counts
        ]


@router.get("/by-category", response_model=List[ClustersByCategoryResponse])
async def list_clusters_by_category(
    current_user: dict = Depends(get_current_user),
    cluster_service: ClusterService = Depends(get_cluster_service),
):
    """
    Get clusters grouped by content category.

    Returns a summary of clusters organized by category,
    useful for displaying a categorized view of the user's content.
    """
    grouped = cluster_service.get_clusters_grouped_by_category(user_id=current_user["user_id"])

    result = []
    for category, clusters in grouped.items():
        total_items = sum(c["item_count"] for c in clusters)
        cluster_responses = [
            ClusterResponse(
                id=str(c["cluster"].id),
                user_id=str(c["cluster"].user_id),
                content_category=c["cluster"].content_category,
                label=c["cluster"].label,
                short_description=c["cluster"].short_description,
                item_count=c["item_count"],
                created_at=c["cluster"].created_at,
                updated_at=c["cluster"].updated_at,
            )
            for c in clusters
        ]
        result.append(
            ClustersByCategoryResponse(
                category=category,
                clusters=cluster_responses,
                total_clusters=len(clusters),
                total_items=total_items,
            )
        )

    # Sort by total_items descending
    result.sort(key=lambda x: x.total_items, reverse=True)
    return result


@router.get("/summary")
async def get_category_summary(
    current_user: dict = Depends(get_current_user),
    cluster_service: ClusterService = Depends(get_cluster_service),
):
    """
    Get summary of clusters per category.

    Returns a quick overview of how many clusters and items
    exist in each content category.
    """
    return cluster_service.get_category_summary(current_user["user_id"])


@router.get("/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(
    cluster_id: str,
    current_user: dict = Depends(get_current_user),
    cluster_service: ClusterService = Depends(get_cluster_service),
):
    """
    Get cluster details by ID.

    Returns cluster details if it belongs to the authenticated user.
    """
    try:
        cluster = cluster_service.get_cluster_by_id(
            cluster_id=cluster_id, user_id=current_user["user_id"]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Get item count
    result = cluster_service.get_cluster_with_items(
        cluster_id=cluster_id, user_id=current_user["user_id"]
    )

    return ClusterResponse(
        id=str(cluster.id),
        user_id=str(cluster.user_id),
        content_category=cluster.content_category,
        label=cluster.label,
        short_description=cluster.short_description,
        item_count=result["item_count"] if result else 0,
        created_at=cluster.created_at,
        updated_at=cluster.updated_at,
    )


@router.get("/{cluster_id}/items", response_model=ClusterWithItemsResponse)
async def get_cluster_items(
    cluster_id: str,
    current_user: dict = Depends(get_current_user),
    cluster_service: ClusterService = Depends(get_cluster_service),
):
    """
    Get cluster with all its items.

    Returns the cluster details along with all items (saves) in the cluster.
    """
    try:
        result = cluster_service.get_cluster_with_items(
            cluster_id=cluster_id, user_id=current_user["user_id"]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    cluster = result["cluster"]
    items = result["items"]

    cluster_response = ClusterResponse(
        id=str(cluster.id),
        user_id=str(cluster.user_id),
        content_category=cluster.content_category,
        label=cluster.label,
        short_description=cluster.short_description,
        item_count=len(items),
        created_at=cluster.created_at,
        updated_at=cluster.updated_at,
    )

    item_responses = [
        ClusterItemResponse(
            save_id=str(item.id),
            shared_content_id=str(item.shared_content_id),
            title=item.shared_content.title,
            thumbnail_url=item.shared_content.thumbnail_url,
            topic_main=item.shared_content.topic_main,
            raw_share_text=item.raw_share_text,
            saved_at=item.created_at,
        )
        for item in items
    ]

    return ClusterWithItemsResponse(cluster=cluster_response, items=item_responses)
