"""
Common Pydantic Schemas for CricXI.
"""

from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class HealthStatus(BaseModel):
    """Health check response schema."""
    status: str = Field(default="ok", description="Server health status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(..., description="Running environment")
    dataset_loaded: bool = Field(..., description="Whether dataset is loaded into memory")
    players_count: int = Field(default=0, description="Total players loaded in dataset")


class ApiResponse(BaseModel, Generic[T]):
    """Standardized generic API response envelope."""
    success: bool = Field(default=True, description="Indicates request success")
    message: str = Field(default="Success", description="Human-readable response message")
    data: Optional[T] = Field(default=None, description="Response payload")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized paginated response."""
    items: List[T] = Field(default_factory=list, description="Page items")
    total: int = Field(..., description="Total available records")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total pages available")

