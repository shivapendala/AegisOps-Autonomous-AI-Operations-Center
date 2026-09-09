"""SQLAlchemy ORM model for Alerts table."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.session import Base


class AlertModel(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(32), default="MEDIUM", nullable=False, index=True)
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)
    source = Column(String(64), default="scikit-learn-detector", nullable=False)
    trigger_value = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    service = relationship("ServiceModel", back_populates="alerts")

    def to_dict(self):
        return {
            "id": self.id,
            "service_id": self.service_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "status": self.status,
            "source": self.source,
            "trigger_value": self.trigger_value,
            "threshold_value": self.threshold_value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
