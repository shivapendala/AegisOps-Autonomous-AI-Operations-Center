-- AegisOps Complete PostgreSQL Schema Definition
-- Production DDL for all core operational entities

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(128) UNIQUE NOT NULL,
    full_name VARCHAR(128),
    role VARCHAR(32) DEFAULT 'OPERATOR' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- 2. Services Table
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) UNIQUE NOT NULL,
    description TEXT,
    status VARCHAR(32) DEFAULT 'HEALTHY' NOT NULL,
    tier VARCHAR(32) DEFAULT 'STANDARD' NOT NULL,
    endpoint_url VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_services_status ON services (status);
CREATE INDEX IF NOT EXISTS idx_services_tier ON services (tier);

-- 3. Metrics Table
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    service_id INTEGER REFERENCES services(id) ON DELETE SET NULL,
    metric_name VARCHAR(128) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(32) DEFAULT '' NOT NULL,
    dimensions JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_metrics_service ON metrics (service_id);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics (metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics (timestamp DESC);

-- 4. Alerts Table
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    service_id INTEGER REFERENCES services(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(32) DEFAULT 'MEDIUM' NOT NULL,
    status VARCHAR(32) DEFAULT 'ACTIVE' NOT NULL,
    source VARCHAR(64) DEFAULT 'scikit-learn-detector' NOT NULL,
    trigger_value DOUBLE PRECISION,
    threshold_value DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_alerts_service ON alerts (service_id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts (severity);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts (status);

-- 5. Incidents Table
CREATE TABLE IF NOT EXISTS incidents (
    id VARCHAR(64) PRIMARY KEY,
    service_id INTEGER REFERENCES services(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(32) DEFAULT 'MEDIUM' NOT NULL,
    status VARCHAR(32) DEFAULT 'OPEN' NOT NULL,
    root_cause TEXT,
    impact_summary TEXT,
    ai_remediation TEXT,
    anomaly_score DOUBLE PRECISION,
    metadata_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_incidents_service ON incidents (service_id);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents (severity);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents (status);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents (created_at DESC);

-- 6. Incident Events Timeline Table
CREATE TABLE IF NOT EXISTS incident_events (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(64) REFERENCES incidents(id) ON DELETE CASCADE NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    description TEXT NOT NULL,
    actor VARCHAR(64) DEFAULT 'AegisOps-Autopilot' NOT NULL,
    event_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_incident_events_incident ON incident_events (incident_id);
CREATE INDEX IF NOT EXISTS idx_incident_events_created ON incident_events (created_at DESC);

-- 7. Recommendations Table
CREATE TABLE IF NOT EXISTS recommendations (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(64) REFERENCES incidents(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    action_type VARCHAR(64) DEFAULT 'REMEDIATION' NOT NULL,
    confidence DOUBLE PRECISION DEFAULT 0.90 NOT NULL,
    priority VARCHAR(16) DEFAULT 'P2' NOT NULL,
    status VARCHAR(32) DEFAULT 'PENDING' NOT NULL,
    generated_by VARCHAR(64) DEFAULT 'AegisOps-AI-LLM' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_recommendations_incident ON recommendations (incident_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_status ON recommendations (status);
