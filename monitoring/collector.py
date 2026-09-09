"""
System Metrics Collector based on psutil.
Extracts real-time host CPU, memory, disk, network, and process metrics.
Robust error handling across operating systems.
"""

from datetime import datetime, timezone
import logging
import platform
import socket
from typing import Any, Dict, List, Optional
import psutil

from aegisops.models.events import SystemTelemetry

logger = logging.getLogger("aegisops.monitoring.collector")


class SystemCollector:
    """Probes the host OS using psutil to harvest system telemetry snapshots."""

    def __init__(self):
        self.host_name = socket.gethostname()
        self.os_type = platform.system()
        # Prime psutil cpu_percent calculation on first init
        psutil.cpu_percent(interval=None)

    def collect(self) -> SystemTelemetry:
        """Collects an instantaneous snapshot of host system telemetry."""
        try:
            cpu_pct = float(psutil.cpu_percent(interval=None))
            vmem = psutil.virtual_memory()
            disk = psutil.disk_usage("/") if self.os_type != "Windows" else psutil.disk_usage("C:\\")
            net = psutil.net_io_counters()
            process_count = len(psutil.pids())

            return SystemTelemetry(
                timestamp=datetime.now(timezone.utc),
                host_name=self.host_name,
                cpu_percent=round(cpu_pct, 2),
                memory_percent=round(vmem.percent, 2),
                memory_used_gb=round(vmem.used / (1024**3), 2),
                memory_total_gb=round(vmem.total / (1024**3), 2),
                disk_percent=round(disk.percent, 2),
                disk_free_gb=round(disk.free / (1024**3), 2),
                network_sent_mb=round(net.bytes_sent / (1024**2), 2),
                network_recv_mb=round(net.bytes_recv / (1024**2), 2),
                process_count=process_count,
            )
        except Exception as exc:
            logger.error("Failed to sample system telemetry: %s", exc, exc_info=True)
            # Fallback safe telemetry record in case of transient probe error
            return SystemTelemetry(
                timestamp=datetime.now(timezone.utc),
                host_name=self.host_name,
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                process_count=0,
            )

    def get_detailed_report(self) -> Dict[str, Any]:
        """Returns deep telemetry diagnostic breakdown including per-core CPU and top processes."""
        try:
            per_cpu = psutil.cpu_percent(percpu=True, interval=None)
            vmem = psutil.virtual_memory()
            swap = psutil.swap_memory()

            top_processes: List[Dict[str, Any]] = []
            for proc in sorted(
                psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
                key=lambda p: (p.info.get("cpu_percent") or 0.0),
                reverse=True,
            )[:8]:
                try:
                    top_processes.append(
                        {
                            "pid": proc.info["pid"],
                            "name": proc.info["name"],
                            "cpu_percent": proc.info.get("cpu_percent") or 0.0,
                            "memory_percent": round(proc.info.get("memory_percent") or 0.0, 2),
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return {
                "host_name": self.host_name,
                "os": self.os_type,
                "per_core_cpu": per_cpu,
                "memory": {
                    "total_gb": round(vmem.total / (1024**3), 2),
                    "available_gb": round(vmem.available / (1024**3), 2),
                    "percent": vmem.percent,
                },
                "swap": {
                    "total_gb": round(swap.total / (1024**3), 2),
                    "used_gb": round(swap.used / (1024**3), 2),
                    "percent": swap.percent,
                },
                "top_processes": top_processes,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.error("Error gathering detailed diagnostics: %s", exc)
            return {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
