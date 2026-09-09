"""SQLAlchemy ORM model for historical telemetry metric logging."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime
from database.session import Base


class MetricLogModel(Base):
    __tablename__ = "metric_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    host_name = Column(String(128), default="localhost", index=True)
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    disk_percent = Column(Float, nullable=False)
    network_sent_mb = Column(Float, default=0.0)
    network_recv_mb = Column(Float, default=0.0)
    process_count = Column(Integer, default=0)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "host_name": self.host_name,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_percent": self.disk_percent,
            "network_sent_mb": self.network_sent_mb,
            "network_recv_mb": self.network_recv_mb,
            "process_count": self.process_count,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
