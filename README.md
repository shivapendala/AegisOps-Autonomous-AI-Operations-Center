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

### System Architecture Diagram

```mermaid
flowchart TD
    subgraph ClientLayer ["Client & Operations Presentation Layer"]
        Browser["React 18 + TypeScript Dashboard<br/>(Tailwind CSS + Recharts + Lucide)"]
        WSClient["Real-time WebSocket Client<br/>(/ws/monitor)"]
        Browser <--> WSClient
    end

    subgraph IngressLayer ["Ingress & Reverse Proxy (Port 5173 / 80)"]
        Nginx["Nginx Alpine Reverse Proxy<br/>(SPA Routing, Gzip, WebSocket Pass-through)"]
    end

    subgraph BackendLayer ["FastAPI Core Services (Port 8000)"]
        FastAPI["FastAPI Application Factory & Lifespan"]
        WSManager["Centralized WebSocket Manager<br/>(Real-Time Broadcast Engine)"]
        
        subgraph MonitoringEngine ["Autonomous Monitoring & Telemetry Subsystem"]
            Collector["System Collector (psutil)<br/>CPU, RAM, Disk, Net, Procs"]
            ThresholdEngine["Alert Rule Engine<br/>Warning & Critical Evaluation"]
            Simulation["Multi-Service Simulation Engine<br/>(Payment, Auth, Order, DB, Notif)"]
        end

        subgraph CorrelationSubsystem ["Event Correlation & Incident Engine"]
            CorrEngine["4-Factor Event Correlation Engine<br/>Score >= 60 -> Incident Clustering"]
            IncManager["Incident Lifecycle State Machine<br/>OPEN -> INVESTIGATING -> RESOLVED -> CLOSED"]
        end

        subgraph AIRCA ["AI Root Cause Analysis Subsystem"]
            RCAInvestigator["Incident Context Collector<br/>(Alerts, Metrics, Services, Audit Logs)"]
            AIProvider{"AI Provider Abstraction"}
            MockAI["Deterministic MockAIProvider<br/>(Zero-Dependency SRE Heuristics)"]
            LLM["LLMProvider<br/>(OpenAI / Azure / Anthropic)"]
        end
    end

    subgraph DatastoreLayer ["Persistence Layer (PostgreSQL 15)"]
        DB[(PostgreSQL Database<br/>Persistent Volume: postgres_data)]
        Tables["Tables: services, metrics, alerts,<br/>incidents, incident_events, recommendations, audit_logs"]
        DB --- Tables
    end

    %% Wiring
    Browser -->|HTTP REST: /api/*| Nginx
    WSClient -->|WebSocket: /ws/*| Nginx
    Nginx -->|Proxy Pass: /api/*| FastAPI
    Nginx -->|Proxy Pass: /ws/*| WSManager

    Collector -->|System Telemetry (2.0s)| ThresholdEngine
    Simulation -->|Simulated Telemetry (2.0s)| ThresholdEngine
    ThresholdEngine -->|Deduplicated Alerts| CorrEngine
    Simulation -->|Cascading Alerts| CorrEngine

    CorrEngine -->|Grouped Incidents| IncManager
    IncManager -->|On Incident Creation| RCAInvestigator
    RCAInvestigator --> AIProvider
    AIProvider --> MockAI
    AIProvider -.->|If API Key Present| LLM
    MockAI -->|Root Cause, Evidence, Recommendations| IncManager

    FastAPI -->|SQLAlchemy Sync + Asyncpg| DB
    IncManager -->|Persist Incidents & Audit Trails| DB
    ThresholdEngine -->|Persist Metrics & Alerts| DB

    ThresholdEngine -.->|Broadcast Metrics & Alerts| WSManager
    IncManager -.->|Broadcast Status Changes| WSManager
    WSManager -.->|JSON Streaming Events| WSClient
```

### Event Correlation Logic
Multiple related alerts are grouped into **ONE incident** rather than triggering redundant alarms:
* **Same Service Match**: $+30$ points
* **Time-Window Match** ($\le 60\text{s}$): $+25$ points
* **Related Metric Affinity** (Knowledge base clusters): $+30$ points
* **Severity Affinity**: $+15$ points
* **Threshold**: Score $\ge 60$ automatically clusters alerts into the existing incident.

---

## 8. Realistic Demo Workflow

Follow this step-by-step walkthrough during presentations or system verification:

```
+---------------+     +-------------+     +-------------------+     +-------------------------+
| Normal System | --> |  CPU Spike  | --> | Database Overload | --> |  API Latency Increase   |
+---------------+     +-------------+     +-------------------+     +-------------------------+
                                                                                 |
                                                                                 v
+------------------+     +-------------------+     +--------------------+     +-------------------+
|  Root Cause &    | <-- | AI Investigation  | <-- | ONE Critical       | <-- |  Multiple Alerts  |
|  Recommendations |     |  (MockAIProvider) |     | Correlated Incident|     | (Event Correlation|
+------------------+     +-------------------+     +--------------------+     +-------------------+
         |
         v
+----------------------+
|  Operator Resolves   |
|  & Closes Incident   |
+----------------------+
```

### Step 1: Normal System
* Click **`[Normal]`** on the top control bar.
* **Observe**:
  * Overall status indicates **SYSTEM: OPERATIONAL**.
  * All 5 microservices in the *Simulated Microservices Telemetry* grid are green (**HEALTHY**).
  * Latencies average $<45\text{ms}$, CPU is $<35\%$, error rates are $<0.1\%$, and database connection pools are $<35\%$.
  * Real-time metrics stream smoothly over the WebSocket without page refresh.

### Step 2: CPU Spike
* Click **`[CPU Spike]`**.
* **Observe**:
  * Compute pressure immediately surges on **Order Service** ($\text{CPU} > 94\%$).
  * A critical warning alert is generated and appears in the **Active Alerts Table**.
  * The system status transitions to **DEGRADED**.

### Step 3: Database Overload
* Click **`[Database Overload]`**.
* **Observe**:
  * **PostgreSQL Database** connection pool saturates to $>96\%$, query latency degrades to $>450\text{ms}$.
  * Cascading pressure affects dependent downstream services (**Payment API** and **Order Service** enter **DEGRADED** states).
  * Additional alerts populate the live stream.

### Step 4 & 5: Combined Payment Failure (API Latency Surge & Multiple Alerts)
* Click **`[Payment Failure]`**.
* **Observe**:
  * Four cascading events fire in rapid succession on **Payment API**:
    1. **CPU Spike**: `cpu_usage = 92.4%` (Critical)
    2. **Database Overload**: `database_connections = 95.6%` (Critical)
    3. **API Latency Surge**: `api_latency = 2.8s` (Critical)
    4. **HTTP Error Surge**: `http_500_errors = 14.8%` (Critical)

### Step 6 & 7: Event Correlation $\to$ ONE Critical Incident
* The **Event Correlation Engine** evaluates all 4 incoming alerts against service, time window, metric affinity, and severity.
* **Observe**:
  * Instead of creating 4 separate confusing incidents, the correlation engine combines them into **EXACTLY ONE unified incident**:
    * **Title**: `Payment Api degradation`
    * **Service**: `Payment API`
    * **Severity**: `CRITICAL`
    * **Correlation Score**: $100\%$
  * The **Active Incidents Panel** displays the single consolidated incident card with tags for all 4 affected metrics (`cpu_usage`, `database_connections`, `api_latency`, `http_500_errors`).

### Step 8 & 9: AI Investigation $\to$ Root Cause
* Click the incident card or click **Details** to open the **Incident Details Modal Console**.
* **Observe**:
  * **AI Diagnosis**: Automated RCA executed by `MockAIProvider` without requiring external API keys.
  * **Probable Root Cause**: `Database connection pool exhaustion`.
  * **Confidence Score**: `91%`.
  * **Evidence Points**:
    * *Database connections increased to 96%*
    * *API latency increased from 200ms to 2.8s*
    * *HTTP 500 errors increased*
    * *CPU increased after database saturation*

### Step 10: Recommended Actions
* In the modal, review the AI remediation plan:
  1. *Increase database connection pool and investigate long-running queries.*
  2. *Enable connection pool keepalive and review slow query log for missing indexes.*
  3. *Implement circuit-breaker pattern to gracefully degrade traffic during DB saturation.*

### Step 11: Operator Resolves Incident
* Click **Start Investigation** $\to$ status transitions to **INVESTIGATING**.
* Click **Resolve Incident** $\to$ enter resolution notes (e.g., *"Scaled connection pool to 64 and restarted worker pods"*) $\to$ status transitions to **RESOLVED** and stamps `resolved_at`.
* Click **Close Incident** $\to$ status transitions to **CLOSED**.
* Click **`[Recover System]`** on the top bar to return all microservices to healthy baseline.

---

## 9. Testing Instructions

AegisOps comes with 66 comprehensive automated unit and integration tests:

```bash
# Run the complete test suite
python -m pytest -p no:asyncio -v tests/
```

### Test Suite Breakdown
* `tests/test_automated_backend.py`: Comprehensive backend tests covering Health, Metrics, Alerts, Thresholds, Correlation, Incidents, Lifecycle transitions, Mock AI, WebSocket, and the 4-part cascading failure scenario.
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
