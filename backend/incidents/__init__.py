"""
AegisOps Incident Management and Event Correlation Package.
"""

from .models import (
    IncidentModel,
    IncidentEventModel,
    IncidentRecommendationModel,
    RecommendationModel,
    AlertModel,
    ServiceModel,
)
from .correlation import (
    compare_service,
    compare_time_window,
    compare_metric_relationship,
    compare_severity_relationship,
    calculate_score,
    find_recent_alerts,
    find_related_alerts,
    correlate_and_group_alerts,
)
from .service import IncidentService

__all__ = [
    "IncidentModel",
    "IncidentEventModel",
    "IncidentRecommendationModel",
    "RecommendationModel",
    "AlertModel",
    "ServiceModel",
    "compare_service",
    "compare_time_window",
    "compare_metric_relationship",
    "compare_severity_relationship",
    "calculate_score",
    "find_recent_alerts",
    "find_related_alerts",
    "correlate_and_group_alerts",
    "IncidentService",
]
