<<<<<<< HEAD
# AegisOps-Autonomous-AI-Operations-Center
=======
# AegisOps - Autonomous AI Operations Center

<div align="center">

![AegisOps Badge](https://img.shields.io/badge/AegisOps-Autonomous%20AI%20Ops-blue.svg)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?logo=typescript)
![Vite](https://img.shields.io/badge/Vite-5.0-646CFF?logo=vite)
![TailwindCSS](https://img.shields.io/badge/Tailwind-3.4-38B2AC?logo=tailwindcss)
![scikit-learn](https://img.shields.io/badge/scikit--learn-IsolationForest-F7931E?logo=scikit-learn)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-336791?logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-green.svg)

</div>

**AegisOps** is an autonomous AI-driven operations center engineered for real-time infrastructure telemetry ingestion, machine-learning anomaly detection, pluggable LLM root cause analysis, and responsive operations dashboarding.

---

## 🌟 Architecture Highlights

* **Frontend**: React + TypeScript + Vite + Tailwind CSS + Recharts
  * Real-time WebSocket streaming of hardware metrics and anomaly signals
  * Dark-mode operations command center UI
  * Responsive time-series charts and active incident triage view
* **Backend**: Python + FastAPI + WebSockets + SQLAlchemy
  * High-performance asynchronous REST and WebSocket streaming engine
  * Structured logging with custom error handling middleware
  * Health check probe reporting database and AI engine readiness
* **Machine Learning**: `scikit-learn` IsolationForest
  * Unsupervised multi-variate outlier detection across CPU, RAM, Disk, and Process count
  * Pre-seeded nominal baselines for instantaneous zero-cold-start accuracy
* **Pluggable LLM Layer**: `BaseLLMService` Strategy Pattern
  * Clean abstract service interface allowing seamless swapping between providers
  * Built-in zero-dependency `MockLLMService` for offline development and testing
  * `OpenAILLMService` stub ready for OpenAI, Azure OpenAI, Ollama, or vLLM
* **Telemetry Monitoring**: `psutil`
  * Deep OS hardware probes (CPU overall and per-core, RAM, swap, disk partitions, network I/O, process count)
  * Standalone monitoring daemon
* **Database**: PostgreSQL with SQLAlchemy 2.0 ORM
  * Automatic SQLite fallback when PostgreSQL is not running locally for rapid development and testing

---

## 📁 Repository Structure

```text
aegisops/
├── aegisops/                  # Core Autonomous Operations & AI Package
│   ├── ai/                    # Scikit-learn anomaly detector & BaseLLMService interface
│   ├── engine/                # Autonomous incident orchestrator
│   └── models/                # Pydantic schemas for telemetry, incidents, and anomalies
├── backend/                   # FastAPI Web & WebSocket Server
│   ├── api/                   # REST routes (health, metrics, incidents, ai) & WebSocket endpoint
│   ├── core/                  # Structured logger & custom exception handling
│   ├── config.py              # Environment configuration via pydantic-settings
│   ├── main.py                # Application entrypoint & lifespan manager
│   ├── requirements.txt       # Backend dependencies
│   └── .env.example           # Backend environment template
├── frontend/                  # React + TypeScript + Vite + Tailwind UI
│   ├── src/                   # React components, WebSocket client, Recharts graphs
│   ├── package.json           # Frontend dependencies
│   ├── vite.config.ts         # Vite configuration
│   └── .env.example           # Frontend environment template
├── database/                  # SQLAlchemy ORM models, session engine & PostgreSQL DDL
├── monitoring/                # psutil hardware collector & background agent
├── docs/                      # Architecture, API specifications, and AI documentation
│   ├── ARCHITECTURE.md
│   ├── API_SPEC.md
│   └── AI_SYSTEM.md
├── tests/                     # Pytest automated test suite
├── requirements.txt           # Unified Python requirements
└── README.md
```

---

## 🚀 Quickstart Guide

### Prerequisites
* Python 3.10+
* Node.js 18+ and npm
* PostgreSQL (optional; automatically falls back to local SQLite if offline)

---

### 1. Backend Setup

```bash
# Optional: create a virtual environment
python -m venv .venv
# On Windows: .venv\Scripts\activate
# On Linux/macOS: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Run unit and integration tests
python -m pytest -p no:asyncio -v tests/

# Start the FastAPI server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Once started, explore:
* **Interactive OpenAPI Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Health Endpoint**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
* **Live Telemetry Snapshot**: [http://localhost:8000/api/v1/metrics/current](http://localhost:8000/api/v1/metrics/current)
* **WebSocket Endpoint**: `ws://localhost:8000/ws/telemetry`

---

### 2. Frontend Setup

```bash
cd frontend

# Copy environment variables
cp .env.example .env

# Install npm dependencies
npm install
# (Note: On Windows PowerShell if script execution is restricted, use: npm.cmd install)

# Start the Vite development server
npm run dev

# Or build for production
npm run build
```

Open [http://localhost:5173](http://localhost:5173) in your browser to view the AegisOps operations dashboard.

---

### 3. Standalone Monitoring Agent (Optional)

You can also run the standalone telemetry collector agent from the command line:

```bash
python monitoring/agent.py 2.0
```

---

## 🧪 Testing

Run the automated test suite:

```bash
python -m pytest -p no:asyncio -v tests/
```

All 13 tests cover:
- Health check endpoints and readiness probes
- Hardware telemetry extraction via psutil
- Multi-variate anomaly detection with scikit-learn
- Pluggable LLM interface contract and mock reasoning engine
- Database ORM operations and incident triage lifecycle

---

## 📄 License & Attribution

This project is an original implementation designed from scratch for the AegisOps Autonomous AI Operations Center under the permissive MIT License. No GPL code is used.
>>>>>>> ec4f946 (initial project setup)
