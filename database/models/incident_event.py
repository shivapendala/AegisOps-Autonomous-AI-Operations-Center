"""SQLAlchemy ORM model for Incident Events timeline table."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database.session import Base


class IncidentEventModel(Base):
    __tablename__ = "incident_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(64), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    actor = Column(String(64), default="AegisOps-Autopilot", nullable=False)
    event_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    incident = relationship("IncidentModel", back_populates="events")

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "event_type": self.event_type,
            "description": self.description,
            "actor": self.actor,
            "event_data": self.event_data or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
