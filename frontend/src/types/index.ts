export interface SystemTelemetry {
  timestamp: string;
  host_name: string;
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb?: number;
  memory_total_gb?: number;
  disk_percent: number;
  disk_free_gb?: number;
  network_sent_mb?: number;
  network_recv_mb?: number;
  process_count: number;
  uptime_seconds?: number;
}

export interface AnomalyScore {
  is_anomaly: boolean;
  score: number;
  confidence: number;
  anomaly_type?: string | null;
  affected_metrics: string[];
  description: string;
}

export interface Alert {
  id: number | string;
  service: string;
  metric: string;
  value: number;
  threshold: number;
  severity: 'WARNING' | 'CRITICAL' | 'INFO' | 'HIGH' | 'MEDIUM' | 'LOW';
  message: string;
  timestamp: string;
  status: 'ACTIVE' | 'RESOLVED' | 'ACKNOWLEDGED' | 'SUPERSEDED';
}

export interface ServiceItem {
  id: number;
  name: string;
  description?: string;
  status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';
  tier: string;
  endpoint_url?: string;
}

export interface TimelineEvent {
  id: string;
  event_type: 'ALERT' | 'INCIDENT' | 'SERVICE' | 'SYSTEM';
  title: string;
  description: string;
  timestamp: string;
  severity?: 'INFO' | 'WARNING' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  actor?: string;
}

export interface Incident {
  id: string;
  service_id?: number;
  service?: string;
  service_name?: string;
  title: string;
  description?: string;
  severity: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'CLOSED';
  root_cause?: string;
  probable_cause?: string;
  impact_summary?: string;
  ai_remediation?: string;
  anomaly_score?: number;
  correlation_score?: number;
  affected_metrics?: string[];
  affected_events?: any[];
  confidence?: number;
  evidence?: string[];
  recommended_actions?: string[];
  metadata_json?: any;
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  events?: Array<{
    id: number;
    event_type: string;
    description: string;
    actor: string;
    created_at: string;
  }>;
  recommendations?: Array<{
    id: number;
    title: string;
    description: string;
    action_type: string;
    confidence: number;
    priority: string;
    status: string;
  }>;
}

export interface HealthStatus {
  status: string;
  app_name: string;
  version: string;
  uptime_seconds: number;
  database: string;
  tables_ready: boolean;
  ai_engine: {
    provider: string;
    anomaly_detector: string;
  };
  timestamp: string;
}

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

export interface WebSocketEvent {
  type:
    | 'INITIAL_STATE'
    | 'METRICS_UPDATE'
    | 'NEW_ALERT'
    | 'ALERT_RESOLVED'
    | 'INCIDENT_UPDATE'
    | 'SERVICE_STATUS_CHANGE'
    | 'PONG';
  data?: any;
  timestamp?: string;
}
