"""
Match History API Router for CricXI.
Provides past simulated matches and head-to-head records (Phase 1 Foundation).
"""

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.match import Match
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.match import MatchResponse

router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=PaginatedResponse[MatchResponse])
def get_match_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> PaginatedResponse[MatchResponse]:
    """Retrieves paginated completed match history."""
    query = db.query(Match).filter(Match.status == "COMPLETED").order_by(Match.completed_at.desc())
    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    matches = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[MatchResponse.model_validate(m) for m in matches],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )

