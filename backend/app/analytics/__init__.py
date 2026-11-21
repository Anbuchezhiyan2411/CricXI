"""
CricXI Analytics Package.
Provides descriptive, inferential, and predictive sports analytics
built on completed match data demonstrating Introduction to Data Science (IDS) principles.
"""

from app.analytics.analytics_router import router as analytics_router
from app.analytics.analytics_service import AnalyticsService

__all__ = ["analytics_router", "AnalyticsService"]
