# AegisOps API Specification

## Base URL
* Local REST API: `http://localhost:8000/api/v1`
* Local WebSocket: `ws://localhost:8000/ws/telemetry`
* Interactive OpenAPI Swagger: `http://localhost:8000/docs`

---

## 1. System Health

### `GET /api/v1/health`
Checks the health of the backend, database, and AI engine.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "app_name": "AegisOps - Autonomous AI Operations Center",
  "version": "0.1.0",
  "environment": "development",
  "uptime_seconds": 124.5,
  "database": "healthy",
  "ai_engine": {
    "provider": "mock",
    "anomaly_detector": "scikit-learn-isolation-forest"
  },
  "timestamp": "2026-09-09T04:45:00.000000+00:00"
}
```

---

## 2. Telemetry & Metrics

### `GET /api/v1/metrics/current`
Returns instantaneous snapshot of host resources probed via psutil.

**Query Parameters**:
* `persist` (bool, optional, default=false): If `true`, saves the record into the database table `metric_logs`.

**Response `200 OK`**:
```json
{
  "timestamp": "2026-09-09T04:45:00.000000+00:00",
  "host_name": "DESKTOP-AEGIS",
  "cpu_percent": 18.5,
  "memory_percent": 42.1,
  "memory_used_gb": 6.74,
  "memory_total_gb": 16.0,
  "disk_percent": 58.2,
  "disk_free_gb": 215.3,
  "network_sent_mb": 1420.5,
  "network_recv_mb": 3520.1,
  "process_count": 165
}
```

### `GET /api/v1/metrics/diagnostics`
Returns deep hardware diagnostics including per-core CPU utilization and top resource-consuming processes.

### `GET /api/v1/metrics/history`
Returns historical telemetry data.

**Query Parameters**:
* `limit` (int, 1-200, default=50)

---

## 3. Incident Management

### `GET /api/v1/incidents`
Lists recorded operational incidents.

**Query Parameters**:
* `status` (string, optional): Filter by status (`OPEN`, `INVESTIGATING`, `MITIGATING`, `RESOLVED`, `CLOSED`).
* `limit` (int, default=50)

### `GET /api/v1/incidents/{incident_id}`
Retrieves full incident report, including scikit-learn anomaly scores and AI root cause analysis.

### `POST /api/v1/incidents`
Manually report or simulate an operational incident.

**Request Body**:
```json
{
  "title": "Database Connection Pool Exhaustion",
  "description": "Active pool connection count reached 100%",
  "severity": "HIGH",
  "root_cause": "Spike in unindexed reporting queries",
  "ai_remediation": "Apply query rate limiting and expand pool size"
}
```

### `POST /api/v1/incidents/{incident_id}/resolve`
Marks an incident as resolved and appends an audit log record.

---

## 4. AI Operational Intelligence

### `GET /api/v1/ai/info`
Returns AI configuration, scikit-learn IsolationForest hyperparameters, and active LLM provider.

### `POST /api/v1/ai/evaluate`
Passes a telemetry payload to the scikit-learn detector. If no body is provided, the current host telemetry is analyzed.

**Response `200 OK`**:
```json
{
  "is_anomaly": false,
  "score": 0.1245,
  "confidence": 0.95,
  "anomaly_type": null,
  "affected_metrics": [],
  "description": "System operating within normal baseline envelope"
}
```

### `POST /api/v1/ai/analyze`
Submits an incident context to the pluggable LLM layer to produce root cause analysis and mitigation recommendations.

---

## 5. WebSocket Telemetry Stream

### `WS /ws/telemetry`
Streams real-time telemetry updates and anomaly scores every 2 seconds.

**Message Format**:
```json
{
  "type": "TELEMETRY_UPDATE",
  "telemetry": {
    "timestamp": "2026-09-09T04:45:00.000000+00:00",
    "host_name": "DESKTOP-AEGIS",
    "cpu_percent": 24.3,
    "memory_percent": 41.8,
    "disk_percent": 58.2,
    "process_count": 168
  },
  "anomaly": {
    "is_anomaly": false,
    "score": 0.142,
    "confidence": 0.95,
    "anomaly_type": null,
    "affected_metrics": [],
    "description": "System operating within normal baseline envelope"
  }
}
```
Client may send `"ping"` to receive `"pong"`.
