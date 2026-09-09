"""
Telemetry Anomaly Detection Engine.
Utilizes scikit-learn IsolationForest combined with adaptive statistical scaling
to detect operational anomalies across CPU, RAM, Disk, and Network telemetry.
Original implementation written specifically for AegisOps.
"""

import logging
from typing import List, Optional, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from aegisops.models.events import AnomalyScore, SystemTelemetry

logger = logging.getLogger("aegisops.ai.anomaly_detector")


class AnomalyDetector:
    """
    Unsupervised multi-variate telemetry anomaly detector based on scikit-learn IsolationForest.
    
    Monitors multidimensional operating metrics:
    [cpu_percent, memory_percent, disk_percent, process_count]
    """

    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100,
        )
        self.is_trained: bool = False
        self._history_window: List[List[float]] = []
        self._min_samples_to_fit: int = 20

        # Pre-seed model with a healthy synthetic baseline so cold start works immediately
        self._seed_baseline()

    def _extract_features(self, telemetry: SystemTelemetry) -> List[float]:
        """Extracts normalized feature vector from a SystemTelemetry record."""
        return [
            float(telemetry.cpu_percent),
            float(telemetry.memory_percent),
            float(telemetry.disk_percent),
            float(telemetry.process_count),
        ]

    def _seed_baseline(self) -> None:
        """Seeds the detector with representative nominal operating ranges [CPU, RAM, Disk, Processes]."""
        rng = np.random.default_rng(self.random_state)
        # 60 samples of nominal operating metrics
        cpu = rng.normal(loc=25.0, scale=8.0, size=60).clip(2.0, 60.0)
        ram = rng.normal(loc=40.0, scale=5.0, size=60).clip(15.0, 70.0)
        disk = rng.normal(loc=50.0, scale=2.0, size=60).clip(30.0, 80.0)
        procs = rng.normal(loc=120.0, scale=15.0, size=60).clip(50.0, 250.0)

        data = np.column_stack([cpu, ram, disk, procs])
        scaled_data = self.scaler.fit_transform(data)
        self.model.fit(scaled_data)
        self.is_trained = True
        logger.info("AnomalyDetector initialized and pre-seeded with baseline envelope")

    def fit_from_telemetry(self, history: List[SystemTelemetry]) -> None:
        """Fits the model on an observed historical sequence of telemetry records."""
        if len(history) < self._min_samples_to_fit:
            logger.warning(
                "Insufficient telemetry records (%d < %d) to fit custom baseline",
                len(history),
                self._min_samples_to_fit,
            )
            return

        features = [self._extract_features(t) for t in history]
        arr = np.array(features)
        scaled_arr = self.scaler.fit_transform(arr)
        self.model.fit(scaled_arr)
        self.is_trained = True
        logger.info("AnomalyDetector successfully refitted on %d telemetry samples", len(history))

    def evaluate_telemetry(self, telemetry: SystemTelemetry) -> AnomalyScore:
        """
        Evaluates a single telemetry snapshot for anomalous deviation.
        Returns an AnomalyScore indicating whether it is an anomaly, severity score,
        and which metric dimensions violated nominal thresholds.
        """
        features = self._extract_features(telemetry)
        self._history_window.append(features)
        if len(self._history_window) > 500:
            self._history_window.pop(0)

        # Scale features using fitted scaler
        raw_arr = np.array([features])
        scaled_arr = self.scaler.transform(raw_arr)

        # Isolation forest: prediction is 1 for inlier, -1 for outlier
        pred = self.model.predict(scaled_arr)[0]
        # decision_function returns negative values for outliers, positive for inliers
        score = float(self.model.decision_function(scaled_arr)[0])

        is_anomaly = bool(pred == -1)
        affected_metrics: List[str] = []

        # Heuristic attribution to identify which metrics are elevated
        if telemetry.cpu_percent > 85.0:
            affected_metrics.append(f"CPU Spike ({telemetry.cpu_percent:.1f}%)")
            is_anomaly = True
        if telemetry.memory_percent > 88.0:
            affected_metrics.append(f"High Memory Pressure ({telemetry.memory_percent:.1f}%)")
            is_anomaly = True
        if telemetry.disk_percent > 92.0:
            affected_metrics.append(f"Critical Disk Utilization ({telemetry.disk_percent:.1f}%)")
            is_anomaly = True

        if is_anomaly:
            confidence = min(1.0, max(0.65, abs(score) * 2.0))
            desc = (
                f"Anomaly detected: {', '.join(affected_metrics)}"
                if affected_metrics
                else f"Multi-variate telemetry anomaly score: {score:.3f}"
            )
            anomaly_type = "MULTIVARIATE_OUTLIER" if not affected_metrics else "RESOURCE_SATURATION"
        else:
            confidence = 0.95
            desc = "System operating within normal baseline envelope"
            anomaly_type = None

        return AnomalyScore(
            is_anomaly=is_anomaly,
            score=round(score, 4),
            confidence=round(confidence, 3),
            anomaly_type=anomaly_type,
            affected_metrics=affected_metrics,
            description=desc,
        )
