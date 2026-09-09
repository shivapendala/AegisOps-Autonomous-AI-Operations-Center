"""SQLAlchemy ORM model for Alerts table."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.session import Base


class AlertModel(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True)
    service = Column(String(128), default="system-host", nullable=False, index=True)
    metric = Column(String(64), default="cpu_usage", nullable=False, index=True)
    value = Column(Float, nullable=False, default=0.0)
    threshold = Column(Float, nullable=False, default=0.0)
    severity = Column(String(32), default="WARNING", nullable=False, index=True)
    message = Column(Text, nullable=False, default="")
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)
    source = Column(String(64), default="aegisops-monitor", nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at = Column(DateTime, nullable=True)

    # Backwards compatibility properties
    @property
    def title(self):
        return f"{self.service}: {self.metric} {self.severity}"

    @property
    def description(self):
        return self.message

    @property
    def trigger_value(self):
        return self.value

    @property
    def threshold_value(self):
        return self.threshold

    # Relationships
    service_rel = relationship("ServiceModel", back_populates="alerts")

    def to_dict(self):
        return {
            "id": self.id,
            "service": self.service,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "severity": self.severity,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status": self.status,
            "source": self.source,
            "service_id": self.service_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            # Backwards compatibility aliases
            "title": self.title,
            "description": self.description,
            "trigger_value": self.trigger_value,
            "threshold_value": self.threshold_value,
        }
