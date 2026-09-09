import { HealthStatus, Incident, SystemTelemetry, AnomalyScore } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function fetchCurrentMetrics(): Promise<SystemTelemetry> {
  const res = await fetch(`${API_BASE}/metrics/current`);
  if (!res.ok) throw new Error(`Fetch metrics failed: ${res.statusText}`);
  return res.json();
}

export async function fetchMetricHistory(limit = 30): Promise<SystemTelemetry[]> {
  const res = await fetch(`${API_BASE}/metrics/history?limit=${limit}`);
  if (!res.ok) throw new Error(`Fetch metric history failed: ${res.statusText}`);
  return res.json();
}

export async function fetchIncidents(status?: string): Promise<Incident[]> {
  const url = status ? `${API_BASE}/incidents?status=${status}` : `${API_BASE}/incidents`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Fetch incidents failed: ${res.statusText}`);
  return res.json();
}

export async function resolveIncident(incidentId: string, notes: string): Promise<Incident> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resolution_notes: notes, actor: 'Operations Console' }),
  });
  if (!res.ok) throw new Error(`Resolve incident failed: ${res.statusText}`);
  return res.json();
}

export async function triggerManualIncident(title: string, description: string, severity = 'HIGH'): Promise<Incident> {
  const res = await fetch(`${API_BASE}/incidents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title,
      description,
      severity,
      root_cause: 'Simulated operational drill event',
      ai_remediation: 'Autopilot triage simulated',
    }),
  });
  if (!res.ok) throw new Error(`Create incident failed: ${res.statusText}`);
  return res.json();
}

export async function evaluateTelemetry(telemetry?: SystemTelemetry): Promise<AnomalyScore> {
  const res = await fetch(`${API_BASE}/ai/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ telemetry }),
  });
  if (!res.ok) throw new Error(`AI evaluate failed: ${res.statusText}`);
  return res.json();
}
