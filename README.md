# AegisOps - Autonomous AI Operations Center

<div align="center">

![AegisOps Badge](https://img.shields.io/badge/AegisOps-Autonomous%20AI%20Ops-blue.svg)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?logo=typescript)
![TailwindCSS](https://img.shields.io/badge/Tailwind-3.4-38B2AC?logo=tailwindcss)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-green.svg)

</div>

**AegisOps** is an autonomous AI-powered Site Reliability Engineering (SRE) and operations platform. It continuously harvests real-time hardware and microservice telemetry, evaluates configurable operational thresholds, deterministically groups cascading alerts into unified incidents via a 4-factor Event Correlation Engine, executes automated Root Cause Analysis (RCA) through a pluggable AI provider architecture, and provides interactive presentation drill controls with an operations command dashboard.

---

## Table of Contents

1. [Requirements](#1-requirements)
2. [Installation](#2-installation)
3. [Environment Configuration](#3-environment-configuration)
4. [Docker Setup (One Command)](#4-docker-setup-one-command)
5. [Local Development](#5-local-development)
6. [API Endpoints](#6-api-endpoints)
7. [Architecture](#7-architecture)
8. [Demo Instructions](#8-demo-instructions)
9. [Testing Instructions](#9-testing-instructions)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Requirements

### For Containerized Execution (Recommended)
* **Docker Desktop** / **Docker Engine**: version 20.10+ (with Compose v2+)
* **RAM**: Minimum 4 GB free
* **Ports**: `5173` (Frontend Dashboard), `8000` (FastAPI REST & WebSocket), `5432` (PostgreSQL)

### For Local Standalone Development
* **Python**: 3.10, 3.11, or 3.14+
* **Node.js**: 18+ and npm
* **PostgreSQL**: 14+ (Optional: application automatically falls back to SQLite if PostgreSQL is offline)

---

## 2. Installation

Clone the repository and enter the project directory:

```bash
git clone https://github.com/shivapendala/smart-home-service-platform.git aegisops
cd aegisops
```

---

## 3. Environment Configuration

Copy the sample environment file to create your local `.env`:

```bash
cp .env.example .env
```

### Key Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Application runtime environment (`development` / `production`) |
| `HOST` | `0.0.0.0` | Binding host address |
| `PORT` | `8000` | Backend API port |
| `CORS_ORIGINS` | `*` | Comma-separated allowed HTTP origins |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@postgres:5432/aegisops` | Async PostgreSQL connection string |
| `DATABASE_URL_SYNC` | `postgresql://postgres:postgres@postgres:5432/aegisops` | Sync SQLAlchemy connection string |
| `DB_FALLBACK_SQLITE` | `true` | When true, seamlessly falls back to local SQLite if PostgreSQL is unreachable |
| `LLM_PROVIDER` | `mock` | AI RCA engine provider: `mock`, `openai`, or `anthropic` |
| `OPENAI_API_KEY` | `""` | OpenAI API key (leave empty to use built-in `MockAIProvider`) |
| `METRICS_POLL_INTERVAL_SECONDS` | `2.0` | Telemetry collection frequency (seconds) |

> [!NOTE]
> No API keys are hardcoded. By default, `LLM_PROVIDER=mock` runs a deterministic, zero-dependency reasoning engine that fully demonstrates root cause analysis, evidence extraction, and remediation planning without external API costs or internet requirements.

---

## 4. Docker Setup (One Command)

To build and run all services in orchestrated containers with persistent database storage, networking, and health checks:

```bash
docker compose up --build
```

### What Docker Compose Launches:
1. **`aegisops-postgres`**: PostgreSQL 15 datastore with persistent volume `postgres_data` and health checks (`pg_isready`).
2. **`aegisops-backend`**: FastAPI backend with `psutil` collector, correlation engine, and simulation runner. Starts after PostgreSQL passes health checks.
3. **`aegisops-frontend`**: Nginx multi-stage alpine container hosting the React + TypeScript single-page app and reverse-proxying `/api/` and `/ws/`.

### Access the Application:
* **Operations Dashboard**: [http://localhost:5173](http://localhost:5173)
* **Backend REST API**: [http://localhost:8000](http://localhost:8000)
* **Interactive OpenAPI Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Health Check Probe**: [http://localhost:8000/api/health](http://localhost:8000/api/health)
* **WebSocket Telemetry Stream**: `ws://localhost:8000/ws/monitor`

To stop the containers:
```bash
docker compose down
```

To stop and remove persistent database volumes:
```bash
docker compose down -v
```

---

## 5. Local Development

You can run the backend and frontend directly on your host machine without Docker.

### 1. Backend Server

```bash
# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend (uses local SQLite fallback if PostgreSQL is not active)
python run.py
# Or directly via uvicorn:
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Development Server

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite live-reloading dev server
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 6. API Endpoints

AegisOps exposes REST endpoints under `/api` (with `/api/v1` aliases):

### System & Health
* `GET /api/health`: System health, DB connection status, uptime, AI provider status.

### Real-Time Metrics & Telemetry
* `GET /api/metrics`: Query persisted timeseries metrics stream (filterable by `service_id`, `metric_name`).
* `GET /api/metrics/current`: Instantaneous host CPU, memory, disk, network, and process telemetry.
* `GET /api/metrics/diagnostics`: Per-core CPU load and top resource-consuming processes.
* `GET /api/metrics/summary`: Combined summary of host metrics and recent service telemetry.

### Alerts & Incidents
* `GET /api/alerts`: List alerts with optional filtering by status (`ACTIVE`, `RESOLVED`, `SUPERSEDED`).
* `GET /api/incidents`: List incidents with status filtering (`OPEN`, `INVESTIGATING`, `RESOLVED`, `CLOSED`).
* `GET /api/incidents/{id}`: Detailed incident view with timeline, related alerts, affected metrics, AI RCA, confidence, and recommended actions.
* `POST /api/incidents/{id}/investigate`: Start operator investigation on an incident.
* `POST /api/incidents/{id}/resolve`: Resolve an incident with operator notes.
* `POST /api/incidents/{id}/close`: Close an incident with post-mortem summary.
* `POST /api/incidents/{id}/analyze`: Trigger on-demand AI Root Cause Analysis.

### Monitored Services & Catalog
* `GET /api/services`: List monitored services with status (`HEALTHY`, `DEGRADED`, `CRITICAL`).
* `POST /api/services`: Register a new microservice.

### Monitoring Simulation & Presentation Controls
* `GET /api/simulation/status`: Current scenario, active simulated alerts, and live telemetry for all 5 simulated services.
* `POST /api/simulation/scenario`: Trigger failure scenario (`NORMAL`, `HIGH_CPU`, `DATABASE_OVERLOAD`, `API_LATENCY_SPIKE`, `ERROR_RATE_SPIKE`, `COMBINED_PAYMENT_FAILURE`, `RECOVER`).
* `POST /api/simulation/reset`: Reset system state back to clean `NORMAL` baseline.

### WebSockets
* `WS /ws/monitor`: Primary bidirectional WebSocket broadcasting real-time metrics, threshold alerts, incident status shifts, and simulation updates.

---

## 7. Architecture

```
                                  +-----------------------------+
                                  |     React + TypeScript      |
                                  |     Operations Dashboard    |
                                  +--------------+--------------+
                                                 |
                                  HTTP REST / WS | ws://.../ws/monitor
                                                 v
+-----------------------------------------------------------------------------------------------+
|                                      AegisOps Backend                                          |
|                                                                                               |
|  +-----------------------+     +--------------------------+     +--------------------------+  |
|  |   System Collector    |     |  Alert Rule Engine       |     | Event Correlation Engine |  |
|  |   (psutil Hardware)   | --> |  (Configurable Warning & | --> | (4-Factor Grouping       |  |
|  +-----------------------+     |   Critical Thresholds)   |     |  Score >= 60 -> Incident)|  |
|                                +--------------------------+     +------------+-------------+  |
|  +-----------------------+                                                   |                |
|  |   Simulation Engine   |                                                   v                |
|  |   (5 Microservices:   | -------------------------------------------> +----+-------------+  |
|  |    Payment, Auth,     |                                              | AI Root Cause    |  |
|  |    Order, DB, Notif)  |                                              | Analysis (RCA)   |  |
|  +-----------------------+                                              | (Mock / LLM)     |  |
|                                                                         +----+-------------+  |
+------------------------------------------------------------------------------|----------------+
                                                                               |
                                                                               v
                                                                  +--------------------------+
                                                                  | PostgreSQL Database (15) |
                                                                  | (Persistent Volume)      |
                                                                  +--------------------------+
```

### Event Correlation Logic
Multiple related alerts are grouped into **ONE incident** rather than triggering redundant alarms:
* **Same Service Match**: $+30$ points
* **Time-Window Match** ($\le 60\text{s}$): $+25$ points
* **Related Metric Affinity** (Knowledge base clusters): $+30$ points
* **Severity Affinity**: $+15$ points
* **Threshold**: Score $\ge 60$ automatically clusters alerts into the existing incident.

---

## 8. Demo Instructions

The AegisOps dashboard includes interactive simulation buttons designed for live presentations and architecture drills.

1. Open the dashboard at [http://localhost:5173](http://localhost:5173).
2. Look at the top **DEMO / SIMULATION SYSTEM** control bar.
3. Test the demonstration failure scenarios:
   - **`[Normal]`**: Baseline operation. All 5 services (Payment API, Authentication API, Order Service, PostgreSQL Database, Notification Service) show green `HEALTHY` status.
   - **`[CPU Spike]`**: Simulates compute saturation on Order Service. Watch CPU rise above $92\%$, critical alerts generate, and the incident panel update in real time.
   - **`[Database Overload]`**: Simulates connection pool exhaustion on PostgreSQL Database (>95%). Demonstrates cascade into degraded query latency.
   - **`[Payment Failure]`** (Cascading Multi-Vector Drill):
     - Simulates simultaneous cascading stress on **Payment API**:
       * CPU: $92\%$
       * Database Connections: $95\%$
       * API Latency: $2.8\text{s}$
       * HTTP 500 Errors: $14.8\%$
     - **Result**: The Event Correlation Engine captures all 4 alerts and groups them into **ONE single unified incident** (`Payment API degradation`).
     - Click the incident card in the **Active Incidents Panel** to inspect the **Incident Details Modal** with the 12 diagnostic dimensions, AI root cause ("Database connection pool exhaustion"), confidence score, evidence list, and recommended remediation actions.
   - **`[Recover System]`**: Instantly resolves active simulation alerts, recovers all services to `HEALTHY`, and returns metrics to baseline.

---

## 9. Testing Instructions

AegisOps comes with 56 comprehensive automated unit and integration tests:

```bash
# Run the complete test suite
python -m pytest -p no:asyncio -v tests/
```

### Test Suite Breakdown
* `tests/test_simulation_engine.py`: Multi-service simulation metrics, failure scenarios, and cascading alert correlation into 1 incident.
* `tests/test_incident_management.py`: Incident lifecycle state transitions (`OPEN` $\to$ `INVESTIGATING` $\to$ `RESOLVED` $\to$ `CLOSED`), database persistence, and detail endpoints.
* `tests/test_ai_rca.py`: Root cause analysis provider abstractions, evidence aggregation, and fallback mechanisms.
* `tests/test_correlation_engine.py`: 4-factor scoring mathematical verification, deduplication, and cascading alert grouping.
* `tests/test_monitoring_engine.py`: Telemetry sampling, configurable threshold breaches, and auto-recovery.
* `tests/test_websocket_monitor.py`: Real-time WebSocket connection lifecycle and event broadcast delivery.
* `tests/test_database.py` & `tests/test_api_endpoints.py`: SQLAlchemy ORM integrity and REST API contract verification.

---

## 10. Troubleshooting

### 1. `WinError 10013: An attempt was made to access a socket in a way forbidden by its access permissions`
* **Cause**: On Windows, Windows NAT (WinNAT) or Hyper-V sometimes reserves port ranges including 8000.
* **Solution**: Either stop and restart the Windows NAT service (`net stop winnat` followed by `net start winnat` in Administrator terminal) or run on an alternate port:
  ```powershell
  python -m uvicorn backend.main:app --host 127.0.0.1 --port 8080
  ```

### 2. `FATAL: database "aegisops" does not exist`
* **Cause**: Local PostgreSQL service is running without the target database created.
* **Behavior**: AegisOps automatically handles this by falling back seamlessly to local SQLite storage (`aegisops_local.db`).
* **Fix for PostgreSQL**: In `psql`, execute `CREATE DATABASE aegisops;`.

### 3. Docker Port Conflicts (`port is already allocated`)
* If ports 5432, 8000, or 5173 are already bound by host processes:
  * Stop local instances: `pg_ctl stop` or terminate background dev servers.
  * Or edit host ports in `docker-compose.yml` (e.g. `"5433:5432"`, `"8001:8000"`, `"5174:80"`).

### 4. WebSocket Disconnected / Reconnecting
* Ensure the backend is reachable at `http://localhost:8000`. The frontend includes an automatic exponential backoff reconnect mechanism and will reconnect automatically once the backend is up.

---

## 📄 License

Distributed under the MIT License. No proprietary or restrictive GPL code is utilized.
