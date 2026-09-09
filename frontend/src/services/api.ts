import { Alert, HealthStatus, Incident, ServiceItem, SystemTelemetry, AnomalyScore } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

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

export async function fetchMetricHistory(limit = 30): Promise<any[]> {
  const res = await fetch(`${API_BASE}/metrics?limit=${limit}`);
  if (!res.ok) throw new Error(`Fetch metric history failed: ${res.statusText}`);
  return res.json();
}

export async function fetchAlerts(status?: string): Promise<Alert[]> {
  const url = status ? `${API_BASE}/alerts?status=${status}` : `${API_BASE}/alerts`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Fetch alerts failed: ${res.statusText}`);
  return res.json();
}

export async function fetchServices(status?: string): Promise<ServiceItem[]> {
  const url = status ? `${API_BASE}/services?status=${status}` : `${API_BASE}/services`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Fetch services failed: ${res.statusText}`);
  return res.json();
}

export async function fetchIncidents(status?: string): Promise<Incident[]> {
  const url = status ? `${API_BASE}/incidents?status=${status}` : `${API_BASE}/incidents`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Fetch incidents failed: ${res.statusText}`);
  return res.json();
}

export async function fetchIncidentDetails(incidentId: string): Promise<Incident> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}`);
  if (!res.ok) throw new Error(`Fetch incident details failed: ${res.statusText}`);
  return res.json();
}

export async function fetchIncidentEvents(incidentId: string): Promise<any[]> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/events`);
  if (!res.ok) throw new Error(`Fetch incident events failed: ${res.statusText}`);
  return res.json();
}

export async function fetchIncidentRecommendations(incidentId: string): Promise<any[]> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/recommendations`);
  if (!res.ok) throw new Error(`Fetch incident recommendations failed: ${res.statusText}`);
  return res.json();
}

export async function investigateIncident(incidentId: string, notes?: string): Promise<Incident> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/investigate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      investigation_notes: notes || 'Investigation initiated by Operations Engineer',
      actor: 'Operations Console',
    }),
  });
  if (!res.ok) throw new Error(`Investigate incident failed: ${res.statusText}`);
  return res.json();
}

export async function resolveIncident(incidentId: string, notes?: string): Promise<Incident> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      resolution_notes: notes || 'Resolved via Operations Console',
      actor: 'Operations Console',
    }),
  });
  if (!res.ok) throw new Error(`Resolve incident failed: ${res.statusText}`);
  return res.json();
}

export async function closeIncident(incidentId: string, notes?: string): Promise<Incident> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/close`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      closure_notes: notes || 'Incident closed by Operations Engineer',
      actor: 'Operations Console',
    }),
  });
  if (!res.ok) throw new Error(`Close incident failed: ${res.statusText}`);
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

export async function fetchSimulationStatus(): Promise<any> {
  const res = await fetch(`${API_BASE}/simulation/status`);
  if (!res.ok) throw new Error(`Fetch simulation status failed: ${res.statusText}`);
  return res.json();
}

export async function setSimulationScenario(scenario: string): Promise<any> {
  const res = await fetch(`${API_BASE}/simulation/scenario`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario }),
  });
  if (!res.ok) throw new Error(`Set simulation scenario failed: ${res.statusText}`);
  return res.json();
}

export async function resetSimulation(): Promise<any> {
  const res = await fetch(`${API_BASE}/simulation/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`Reset simulation failed: ${res.statusText}`);
  return res.json();
}

export async function triggerPaymentFailure(): Promise<any> {
  const res = await fetch(`${API_BASE}/simulation/payment-failure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`Trigger payment failure failed: ${res.statusText}`);
  return res.json();
}

export async function approveRecommendation(
  incidentId: string,
  recId: number,
  operator = 'Human Operator',
  notes = 'Approved via Incident Details Console'
): Promise<any> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/recommendations/${recId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operator, notes }),
  });
  if (!res.ok) throw new Error(`Approve recommendation failed: ${res.statusText}`);
  return res.json();
}

export async function rejectRecommendation(
  incidentId: string,
  recId: number,
  operator = 'Human Operator',
  reason = 'Rejected via Incident Details Console'
): Promise<any> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/recommendations/${recId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operator, reason }),
  });
  if (!res.ok) throw new Error(`Reject recommendation failed: ${res.statusText}`);
  return res.json();
}

export async function executeRecommendation(
  incidentId: string,
  recId: number,
  operator = 'Human Operator',
  executionNotes = 'Executed with operator authorization'
): Promise<any> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/recommendations/${recId}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operator, execution_notes: executionNotes }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Execute recommendation failed: ${res.statusText}`);
  }
  return res.json();
}
