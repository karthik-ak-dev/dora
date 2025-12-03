"""
Cluster-related Pydantic schemas.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from ..models.enums import ClusterType


class ClusterResponse(BaseModel):
    """Response for cluster."""
    id: str
    user_id: str
    label: str
    cluster_type: Optional[ClusterType] = None
    short_description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
