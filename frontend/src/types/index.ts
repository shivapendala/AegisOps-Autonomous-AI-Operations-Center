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
}

export interface AnomalyScore {
  is_anomaly: boolean;
  score: number;
  confidence: number;
  anomaly_type?: string | null;
  affected_metrics: string[];
  description: string;
}

export interface Incident {
  id: string;
  title: string;
  description: string;
  severity: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'OPEN' | 'INVESTIGATING' | 'MITIGATING' | 'RESOLVED' | 'CLOSED';
  root_cause?: string;
  ai_remediation?: string;
  anomaly_score?: number;
  created_at: string;
  updated_at: string;
}

export interface HealthStatus {
  status: string;
  app_name: string;
  version: string;
  uptime_seconds: number;
  database: string;
  ai_engine: {
    provider: string;
    anomaly_detector: string;
  };
  timestamp: string;
}

export interface WebSocketTelemetryMessage {
  type: 'TELEMETRY_UPDATE';
  telemetry: SystemTelemetry;
  anomaly: AnomalyScore;
}
