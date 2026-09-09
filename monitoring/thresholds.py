"""
Configurable Monitoring Thresholds.
Defines warning and critical operational boundaries for CPU, Memory, and Disk metrics.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class MetricThreshold:
    warning: float
    critical: float


@dataclass
class ThresholdConfig:
    """Configurable system metric thresholds."""
    cpu: MetricThreshold
    memory: MetricThreshold
    disk: MetricThreshold

    @classmethod
    def default(cls) -> "ThresholdConfig":
        """
        Default thresholds specified by AegisOps operations standards:
        CPU: warning = 70%, critical = 90%
        Memory: warning = 75%, critical = 90%
        Disk: warning = 80%, critical = 90%
        """
        return cls(
            cpu=MetricThreshold(
                warning=float(os.getenv("THRESHOLD_CPU_WARNING", "70.0")),
                critical=float(os.getenv("THRESHOLD_CPU_CRITICAL", "90.0")),
            ),
            memory=MetricThreshold(
                warning=float(os.getenv("THRESHOLD_MEMORY_WARNING", "75.0")),
                critical=float(os.getenv("THRESHOLD_MEMORY_CRITICAL", "90.0")),
            ),
            disk=MetricThreshold(
                warning=float(os.getenv("THRESHOLD_DISK_WARNING", "80.0")),
                critical=float(os.getenv("THRESHOLD_DISK_CRITICAL", "90.0")),
            ),
        )
