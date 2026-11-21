"""
Match History API Router for CricXI.
Provides past simulated matches, head-to-head records, and full scorecards.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.match import Match, MatchInnings
from app.models.room import Room, RoomPlayer
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.history import (
    InningsSummaryInfo,
    MatchHistoryItemResponse,
    MatchHistoryDetailResponse,
)
from app.match.match_service import MatchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["History"])


def _build_match_history_item(m: Match, db: Session) -> MatchHistoryItemResponse:
    """Builds a rich MatchHistoryItemResponse with team names, scores, and awards."""
    room = m.room
    room_code = room.room_code if room else f"M{m.id:04d}"

    # Team identification
    host_p = next((p for p in room.players if p.is_host or p.user_id == m.team1_user_id), None) if room else None
    guest_p = next((p for p in room.players if not p.is_host or p.user_id == m.team2_user_id), None) if room else None

    team1_name = host_p.username if host_p else m.team1_user_id
    team2_name = guest_p.username if guest_p else m.team2_user_id

    # Toss info
    toss_winner_name = None
    if m.toss_winner_id:
        if host_p and m.toss_winner_id == host_p.user_id:
            toss_winner_name = team1_name
        elif guest_p and m.toss_winner_id == guest_p.user_id:
            toss_winner_name = team2_name
        else:
            toss_winner_name = m.toss_winner_id

    # Winner name
    winner_name = None
    if m.winner_user_id:
        if host_p and m.winner_user_id == host_p.user_id:
            winner_name = team1_name
        elif guest_p and m.winner_user_id == guest_p.user_id:
            winner_name = team2_name
        else:
            winner_name = m.winner_user_id
    elif m.status.upper() == "TIED":
        winner_name = "Match Tied"

    # Innings summaries
    inn1 = next((i for i in m.innings if i.innings_number == 1), None)
    inn2 = next((i for i in m.innings if i.innings_number == 2), None)

    inn1_summary = None
    if inn1:
        inn1_team = team1_name if inn1.batting_team_user_id == m.team1_user_id else team2_name
        crr1 = round(inn1.total_runs / max(0.1, (inn1.legal_balls_bowled / 6.0)), 2)
        inn1_summary = InningsSummaryInfo(
            innings_number=1,
            team_name=inn1_team,
            team_user_id=inn1.batting_team_user_id,
            total_runs=inn1.total_runs,
            total_wickets=inn1.total_wickets,
            total_overs=inn1.total_overs,
            run_rate=crr1,
            display_score=f"{inn1.total_runs}/{inn1.total_wickets} ({inn1.total_overs:.1f} ov)",
        )

    inn2_summary = None
    if inn2:
        inn2_team = team1_name if inn2.batting_team_user_id == m.team1_user_id else team2_name
        crr2 = round(inn2.total_runs / max(0.1, (inn2.legal_balls_bowled / 6.0)), 2)
        inn2_summary = InningsSummaryInfo(
            innings_number=2,
            team_name=inn2_team,
            team_user_id=inn2.batting_team_user_id,
            total_runs=inn2.total_runs,
            total_wickets=inn2.total_wickets,
            total_overs=inn2.total_overs,
            run_rate=crr2,
            display_score=f"{inn2.total_runs}/{inn2.total_wickets} ({inn2.total_overs:.1f} ov)",
        )

    # Player of the match
    potm_name = m.player_of_the_match
    potm_details = m.player_of_the_match_details
    if not potm_name and (inn1 or inn2):
        try:
            potm_name, potm_details = MatchService._calculate_player_of_the_match(db, m, inn1, inn2)
        except Exception:
            pass

    return MatchHistoryItemResponse(
        id=m.id,
        room_id=m.room_id,
        room_code=room_code,
        match_date=m.completed_at or m.created_at,
        status=m.status.upper(),
        team1_user_id=m.team1_user_id,
        team2_user_id=m.team2_user_id,
        team1_name=team1_name,
        team2_name=team2_name,
        toss_winner_name=toss_winner_name,
        toss_decision=m.toss_decision,
        winner_user_id=m.winner_user_id,
        winner_name=winner_name,
        result_margin=m.result_margin,
        innings1=inn1_summary,
        innings2=inn2_summary,
        player_of_the_match=potm_name,
        player_of_the_match_details=potm_details,
        has_full_scorecard=True,
    )


@router.get("", response_model=PaginatedResponse[MatchHistoryItemResponse])
def get_match_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> PaginatedResponse[MatchHistoryItemResponse]:
    """Retrieves paginated completed match history with normalized statuses and full metrics."""
    # Normalize statuses: accepts "COMPLETED", "TIED", "FINISHED", "MATCH COMPLETED" case-insensitively
    query = (
        db.query(Match)
        .filter(func.upper(Match.status).in_(["COMPLETED", "TIED", "FINISHED", "MATCH COMPLETED"]))
        .order_by(func.coalesce(Match.completed_at, Match.created_at).desc())
    )

    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    matches = query.offset((page - 1) * page_size).limit(page_size).all()

    items = [_build_match_history_item(m, db) for m in matches]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{match_id}", response_model=ApiResponse[MatchHistoryDetailResponse])
def get_match_history_detail(
    match_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[MatchHistoryDetailResponse]:
    """Retrieves authoritative full scorecard and telemetry for any completed historical match."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Match {match_id} not found.")

    item_info = _build_match_history_item(match, db)
    scorecard = MatchService.get_match_scorecard_by_id(db, match_id)

    return ApiResponse(
        success=True,
        message=f"Scorecard for match {match_id} retrieved successfully.",
        data=MatchHistoryDetailResponse(
            match_id=match.id,
            room_code=item_info.room_code,
            match_info=item_info,
            scorecard=scorecard,
        ),
    )
