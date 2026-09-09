"""SQLAlchemy ORM model for AI Recommendations table."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.session import Base


class RecommendationModel(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(64), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    action_type = Column(String(64), default="REMEDIATION", nullable=False)
    confidence = Column(Float, default=0.90, nullable=False)
    priority = Column(String(16), default="P2", nullable=False)
    status = Column(String(32), default="PENDING", nullable=False, index=True)
    generated_by = Column(String(64), default="AegisOps-AI-LLM", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    incident = relationship("IncidentModel", back_populates="recommendations")

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "action_type": self.action_type,
            "confidence": self.confidence,
            "priority": self.priority,
            "status": self.status,
            "generated_by": self.generated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
