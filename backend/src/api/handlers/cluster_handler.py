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
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from ...shared.schemas.cluster import ClusterResponse
from ...shared.services.cluster_service import ClusterService
from ..dependencies.services import get_cluster_service
from ..dependencies.auth import get_current_user

router = APIRouter()


@router.get("", response_model=List[ClusterResponse])
async def list_clusters(
    current_user: dict = Depends(get_current_user),
    cluster_service: ClusterService = Depends(get_cluster_service)
):
    """
    List user's clusters.
    
    Returns all clusters belonging to the authenticated user.
    """
    clusters = cluster_service.get_user_clusters(current_user["user_id"])
    return [ClusterResponse.from_orm(cluster) for cluster in clusters]


@router.get("/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(
    cluster_id: str,
    current_user: dict = Depends(get_current_user),
    cluster_service: ClusterService = Depends(get_cluster_service)
):
    """
    Get cluster details by ID.
    
    Returns cluster details if it belongs to the authenticated user.
    """
    try:
        cluster = cluster_service.get_cluster_by_id(
            cluster_id=cluster_id,
            user_id=current_user["user_id"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    return ClusterResponse.from_orm(cluster)

