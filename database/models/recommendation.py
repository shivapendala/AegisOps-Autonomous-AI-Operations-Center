"""SQLAlchemy ORM model for Incident Recommendations table."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.session import Base


class IncidentRecommendationModel(Base):
    __tablename__ = "incident_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(64), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(Text, nullable=False)
    priority = Column(String(16), default="HIGH", nullable=False)
    status = Column(String(32), default="PENDING", nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    # Additional metadata fields for AI RCA engine compatibility
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    action_type = Column(String(64), default="REMEDIATION", nullable=True)
    confidence = Column(Float, default=0.90, nullable=True)
    generated_by = Column(String(64), default="AegisOps-AI-LLM", nullable=True)

    # Relationships
    incident = relationship("IncidentModel", back_populates="recommendations")

    def __init__(self, **kwargs):
        # Allow passing 'action' or 'title'/'description' interchangeably
        if "action" not in kwargs:
            kwargs["action"] = kwargs.get("title") or kwargs.get("description") or "Recommended Remediation"
        if "title" not in kwargs:
            kwargs["title"] = kwargs.get("action", "")
        if "description" not in kwargs:
            kwargs["description"] = kwargs.get("action", "")
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "action": self.action,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "title": self.title or self.action,
            "description": self.description or self.action,
            "action_type": self.action_type or "REMEDIATION",
            "confidence": self.confidence,
            "generated_by": self.generated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Backward compatibility alias
RecommendationModel = IncidentRecommendationModel

