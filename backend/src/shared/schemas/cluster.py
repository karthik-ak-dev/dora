"""
Cluster-related Pydantic schemas.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from ..models.enums import ContentCategory


class ClusterResponse(BaseModel):
    """
    Response for cluster.

    Clusters group user's saves WITHIN a content_category.
    All items in a cluster share the same content_category.
    """

    id: str
    user_id: str
    content_category: ContentCategory = Field(
        description="The category this cluster belongs to (Travel, Food, Tech, etc.)"
    )
    label: str = Field(
        description="AI-generated human-readable name (e.g., 'Cafe Hopping in Indiranagar')"
    )
    short_description: Optional[str] = Field(None, description="AI-generated one-sentence summary")
    item_count: int = Field(default=0, description="Number of items in this cluster")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClusterWithItemsResponse(BaseModel):
    """Response for cluster with its items."""

    cluster: ClusterResponse
    items: List["ClusterItemResponse"]


class ClusterItemResponse(BaseModel):
    """Response for an item within a cluster."""

    save_id: str
    shared_content_id: str
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    topic_main: Optional[str] = None
    raw_share_text: Optional[str] = None
    saved_at: datetime

    class Config:
        from_attributes = True


class ClustersByCategoryResponse(BaseModel):
    """Response for clusters grouped by category."""

    category: ContentCategory
    clusters: List[ClusterResponse]
    total_clusters: int
    total_items: int


class CreateClusterRequest(BaseModel):
    """Request to manually create a cluster (future feature)."""

    content_category: ContentCategory
    label: str
    short_description: Optional[str] = None
    save_ids: List[str] = Field(description="List of user_content_save IDs to add to the cluster")
