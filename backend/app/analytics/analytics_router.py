"""
FastAPI Router for CricXI Sports Analytics & Data Science.
Exposes REST endpoints computing empirical analytics from completed match history.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import ApiResponse
from app.analytics.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


class WinPredictionRequestSchema(BaseModel):
    team_a_rating: float = Field(default=80.0, ge=30.0, le=100.0, description="Average overall rating of Team A")
    team_b_rating: float = Field(default=75.0, ge=30.0, le=100.0, description="Average overall rating of Team B")
    toss_winner: str = Field(default="team_a", description="'team_a' or 'team_b'")
    toss_decision: str = Field(default="BAT", description="'BAT' or 'BOWL'")


@router.get("/summary", response_model=ApiResponse[Dict[str, Any]])
def get_analytics_summary(db: Session = Depends(get_db)) -> ApiResponse[Dict[str, Any]]:
    """Retrieves executive summary of completed matches, hypothesis tests, and statistics."""
    summary = AnalyticsService.get_summary(db)
    return ApiResponse(
        success=True,
        message="Analytics summary retrieved successfully.",
        data=summary,
    )


@router.get("/toss-analysis", response_model=ApiResponse[Dict[str, Any]])
@router.get("/toss-hypothesis", response_model=ApiResponse[Dict[str, Any]])
def get_toss_analysis(db: Session = Depends(get_db)) -> ApiResponse[Dict[str, Any]]:
    """
    Section 1 (Main IDS Feature):
    Evaluates Toss Winner vs Match Winner using a One-Sample Proportion Z-Test.
    H0: p = 0.5 (Winning toss does not affect match outcome)
    H1: p != 0.5 (Winning toss has a statistically significant effect)
    """
    result = AnalyticsService.get_toss_analysis(db)
    return ApiResponse(
        success=True,
        message="Toss analysis and hypothesis test computed successfully.",
        data=result,
    )


@router.get("/batting-analysis", response_model=ApiResponse[Dict[str, Any]])
@router.get("/bat-first-vs-chase", response_model=ApiResponse[Dict[str, Any]])
def get_batting_analysis(db: Session = Depends(get_db)) -> ApiResponse[Dict[str, Any]]:
    """
    Section 2:
    Compares Batting First vs Bowling First (Chasing) win percentages and average scores.
    """
    result = AnalyticsService.get_batting_analysis(db)
    return ApiResponse(
        success=True,
        message="Batting strategy analysis computed successfully.",
        data=result,
    )


@router.get("/team-rating", response_model=ApiResponse[Dict[str, Any]])
@router.get("/team-rating-correlation", response_model=ApiResponse[Dict[str, Any]])
def get_team_rating_analysis(db: Session = Depends(get_db)) -> ApiResponse[Dict[str, Any]]:
    """
    Section 3:
    Computes Pearson Correlation and Linear Regression between Average Team Rating advantage and victory.
    """
    result = AnalyticsService.get_team_rating_analysis(db)
    return ApiResponse(
        success=True,
        message="Team rating correlation and regression computed successfully.",
        data=result,
    )


@router.get("/player-performance", response_model=ApiResponse[Dict[str, Any]])
def get_player_performance_outliers(db: Session = Depends(get_db)) -> ApiResponse[Dict[str, Any]]:
    """
    Section 4:
    Detects player performance outliers using standardized Z-Scores.
    Identifies Elite Performers (Z > +2.0) and Underperformers (Z < -2.0).
    """
    result = AnalyticsService.get_player_performance(db)
    return ApiResponse(
        success=True,
        message="Player performance outliers computed successfully.",
        data=result,
    )


@router.get("/match-statistics", response_model=ApiResponse[Dict[str, Any]])
def get_match_statistics(db: Session = Depends(get_db)) -> ApiResponse[Dict[str, Any]]:
    """
    Section 5:
    Univariate descriptive statistics (Mean, Median, Mode, Variance, Std Dev, IQR)
    for total score, 1st innings score, 2nd innings score, and total wickets.
    """
    result = AnalyticsService.get_match_statistics(db)
    return ApiResponse(
        success=True,
        message="Match score and wicket distributions computed successfully.",
        data=result,
    )


@router.get("/correlation-matrix", response_model=ApiResponse[Dict[str, Any]])
def get_correlation_matrix(db: Session = Depends(get_db)) -> ApiResponse[Dict[str, Any]]:
    """
    Section 7:
    Pairwise Pearson correlation matrix for correlation heatmap visualization.
    """
    result = AnalyticsService.get_correlation_matrix(db)
    return ApiResponse(
        success=True,
        message="Correlation matrix computed successfully.",
        data=result,
    )


@router.get("/win-prediction", response_model=ApiResponse[Dict[str, Any]])
def predict_win_probability_get(
    team_a_rating: float = Query(default=80.0, ge=30.0, le=100.0, description="Average overall rating of Team A"),
    team_b_rating: float = Query(default=75.0, ge=30.0, le=100.0, description="Average overall rating of Team B"),
    toss_winner: str = Query(default="team_a", description="'team_a' or 'team_b'"),
    toss_decision: str = Query(default="BAT", description="'BAT' or 'BOWL'"),
    db: Session = Depends(get_db),
) -> ApiResponse[Dict[str, Any]]:
    """
    Section 6:
    Predicts victory probabilities for Team A vs Team B using Scikit-Learn Logistic Regression (GET with query parameters).
    """
    result = AnalyticsService.predict_win_probability(
        team_a_rating=team_a_rating,
        team_b_rating=team_b_rating,
        toss_winner=toss_winner,
        toss_decision=toss_decision,
        db=db,
    )
    return ApiResponse(
        success=True,
        message="Win probability prediction generated successfully.",
        data=result,
    )


@router.post("/predict-win", response_model=ApiResponse[Dict[str, Any]])
@router.post("/win-prediction", response_model=ApiResponse[Dict[str, Any]])
def predict_win_probability_post(
    payload: WinPredictionRequestSchema,
    db: Session = Depends(get_db),
) -> ApiResponse[Dict[str, Any]]:
    """
    Section 6:
    Predicts victory probabilities for Team A vs Team B using Scikit-Learn Logistic Regression (POST with JSON body).
    """
    result = AnalyticsService.predict_win_probability(
        team_a_rating=payload.team_a_rating,
        team_b_rating=payload.team_b_rating,
        toss_winner=payload.toss_winner,
        toss_decision=payload.toss_decision,
        db=db,
    )
    return ApiResponse(
        success=True,
        message="Win probability prediction generated successfully.",
        data=result,
    )


@router.post("/generate-demo-data", response_model=ApiResponse[Dict[str, Any]])
@router.post("/generate-demo", response_model=ApiResponse[Dict[str, Any]])
@router.post("/demo", response_model=ApiResponse[Dict[str, Any]])
def generate_demo_matches(
    count: int = Query(default=15, ge=5, le=50, description="Number of demo matches to synthesize"),
    db: Session = Depends(get_db),
) -> ApiResponse[Dict[str, Any]]:
    """
    Synthesizes realistic historical completed matches into the database
    for testing and instant demonstration of the analytics dashboard.
    """
    result = AnalyticsService.generate_demo_matches(db, count=count)
    return ApiResponse(
        success=result["success"],
        message=result["message"],
        data=result,
    )
