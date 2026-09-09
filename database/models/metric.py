"""SQLAlchemy ORM model for Metrics table."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database.session import Base


class MetricModel(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True)
    metric_name = Column(String(128), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(32), default="", nullable=False)
    dimensions = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    service = relationship("ServiceModel", back_populates="metrics")

    def to_dict(self):
        return {
            "id": self.id,
            "service_id": self.service_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "dimensions": self.dimensions or {},
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
