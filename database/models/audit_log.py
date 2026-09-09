"""SQLAlchemy ORM model for Autonomous Action and Remediation Audit Logs."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from database.session import Base


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(128), nullable=False, index=True)
    actor = Column(String(64), default="AegisOps-Autopilot")
    target = Column(String(128), nullable=True)
    details = Column(Text, nullable=True)
    status = Column(String(32), default="SUCCESS")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "actor": self.actor,
            "target": self.target,
            "details": self.details,
            "status": self.status,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
