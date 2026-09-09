"""SQLAlchemy ORM model for Monitored Services."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from database.session import Base


class ServiceModel(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(32), default="HEALTHY", nullable=False, index=True)
    tier = Column(String(32), default="STANDARD", nullable=False)
    endpoint_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    metrics = relationship("MetricModel", back_populates="service", cascade="all, delete-orphan")
    alerts = relationship("AlertModel", back_populates="service_rel", cascade="all, delete-orphan")
    incidents = relationship("IncidentModel", back_populates="service")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "tier": self.tier,
            "endpoint_url": self.endpoint_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
