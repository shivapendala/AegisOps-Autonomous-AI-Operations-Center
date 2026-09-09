"""SQLAlchemy ORM model for Incident Events timeline table."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database.session import Base


class IncidentEventModel(Base):
    __tablename__ = "incident_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(64), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=True, index=True)
    event_type = Column(String(64), default="ALERT_ATTACHED", nullable=True)
    description = Column(Text, default="", nullable=True)
    actor = Column(String(64), default="AegisOps-Autopilot", nullable=True)
    event_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    incident = relationship("IncidentModel", back_populates="events")
    alert = relationship("AlertModel", foreign_keys=[alert_id], lazy="joined")

    def to_dict(self):
        data = {
            "id": self.id,
            "incident_id": self.incident_id,
            "alert_id": self.alert_id,
            "event_type": self.event_type or ("ALERT_ATTACHED" if self.alert_id else "EVENT"),
            "description": self.description or (f"Alert #{self.alert_id} attached to incident" if self.alert_id else ""),
            "actor": self.actor or "AegisOps-Autopilot",
            "event_data": self.event_data or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if self.alert:
            data["alert"] = self.alert.to_dict()
        return data
