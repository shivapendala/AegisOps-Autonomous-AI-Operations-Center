"""SQLAlchemy ORM model for Operations Incidents table."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database.session import Base


class IncidentModel(Base):
    __tablename__ = "incidents"

    id = Column(String(64), primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True)
    service_name = Column(String(128), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(32), default="MEDIUM", nullable=False, index=True)
    status = Column(String(32), default="OPEN", nullable=False, index=True)
    root_cause = Column(Text, nullable=True)
    probable_cause = Column(Text, nullable=True)
    impact_summary = Column(Text, nullable=True)
    ai_remediation = Column(Text, nullable=True)
    anomaly_score = Column(Float, nullable=True)
    correlation_score = Column(Float, nullable=True, default=100.0)
    affected_metrics = Column(JSON, nullable=True)
    affected_events = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    service = relationship("ServiceModel", back_populates="incidents")
    events = relationship("IncidentEventModel", back_populates="incident", cascade="all, delete-orphan", order_by="IncidentEventModel.created_at")
    recommendations = relationship("RecommendationModel", back_populates="incident", cascade="all, delete-orphan")

    def to_dict(self, include_relations: bool = False):
        resolved_service_name = self.service.name if self.service else self.service_name
        data = {
            "id": self.id,
            "service_id": self.service_id,
            "service_name": resolved_service_name,
            "service": resolved_service_name,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "status": self.status,
            "root_cause": self.root_cause,
            "probable_cause": self.probable_cause or self.root_cause,
            "impact_summary": self.impact_summary,
            "ai_remediation": self.ai_remediation,
            "anomaly_score": self.anomaly_score,
            "correlation_score": self.correlation_score,
            "affected_metrics": self.affected_metrics or [],
            "affected_events": self.affected_events or [],
            "metadata": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
        if include_relations:
            data["events"] = [e.to_dict() for e in self.events]
            data["recommendations"] = [r.to_dict() for r in self.recommendations]
        return data
