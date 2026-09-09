import React, { useState } from 'react';
import { AlertOctagon, Bot, CheckCircle2, ShieldCheck, Sparkles } from 'lucide-react';
import { Incident } from '../types';

interface ActiveIncidentsPanelProps {
  incidents: Incident[];
  onResolve: (id: string) => Promise<void>;
  onSimulateDrill: () => Promise<void>;
  onSelectIncident?: (incident: Incident) => void;
  loading: boolean;
}

export const ActiveIncidentsPanel: React.FC<ActiveIncidentsPanelProps> = ({
  incidents,
  onResolve,
  onSimulateDrill,
  onSelectIncident,
  loading,
}) => {
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [drillPending, setDrillPending] = useState(false);

  const activeIncidents = incidents.filter(
    (i) => i.status.toUpperCase() !== 'RESOLVED' && i.status.toUpperCase() !== 'CLOSED'
  );

  const handleResolveClick = async (id: string) => {
    setResolvingId(id);
    try {
      await onResolve(id);
    } finally {
      setResolvingId(null);
    }
  };

  const handleDrillClick = async () => {
    setDrillPending(true);
    try {
      await onSimulateDrill();
    } finally {
      setDrillPending(false);
    }
  };

  const renderSeverityBadge = (severity: string) => {
    const s = severity.toUpperCase();
    if (s === 'CRITICAL') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-red-100 text-red-700 border border-red-300">
          CRITICAL
        </span>
      );
    }
    if (s === 'HIGH') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-100 text-amber-800 border border-amber-300">
          HIGH
        </span>
      );
    }
    if (s === 'MEDIUM') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-yellow-100 text-yellow-800 border border-yellow-300">
          MEDIUM
        </span>
      );
    }
    return (
      <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-slate-100 text-slate-700 border border-slate-300">
        LOW
      </span>
    );
  };

  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
        ' · ' +
        d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return ts;
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-200">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-600">
            <AlertOctagon className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900 tracking-wide">Active Incidents Panel</h2>
              <span className="px-2 py-0.5 text-xs font-mono font-bold rounded-full bg-red-100 text-red-700 border border-red-300">
                {activeIncidents.length} Active
              </span>
            </div>
            <p className="text-xs text-slate-500">Autonomous triage, root cause analysis & mitigation engine</p>
          </div>
        </div>

        <button
          onClick={handleDrillClick}
          disabled={drillPending || loading}
          className="px-3.5 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 border border-red-600 text-white text-xs font-semibold flex items-center gap-2 transition self-start sm:self-auto shadow-sm shadow-red-500/20 disabled:opacity-50"
        >
          <Bot className="h-4 w-4" />
          {drillPending ? 'Simulating...' : 'Simulate Ops Drill'}
        </button>
      </div>

      {/* Incidents List */}
      {activeIncidents.length === 0 ? (
        <div className="py-10 text-center flex flex-col items-center justify-center space-y-3">
          <div className="p-3 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600">
            <ShieldCheck className="h-8 w-8" />
          </div>
          <p className="text-sm font-bold text-slate-900">No Active Incidents Detected</p>
          <p className="text-xs text-slate-500 max-w-md">
            All services and telemetry metrics are healthy. The AI engine is actively monitoring incoming telemetry streams.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {activeIncidents.map((incident) => (
            <div
              key={incident.id}
              className="rounded-lg border border-slate-200 bg-slate-50/50 p-4 transition hover:border-red-300 hover:bg-red-50/30 shadow-sm"
            >
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                <div
                  className="space-y-1.5 flex-1 cursor-pointer"
                  onClick={() => onSelectIncident && onSelectIncident(incident)}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-red-700 bg-red-100 px-2 py-0.5 rounded border border-red-200">
                      {incident.id}
                    </span>
                    {renderSeverityBadge(incident.severity)}
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-100 text-amber-800 border border-amber-300">
                      {incident.status}
                    </span>
                    {incident.service_name && (
                      <span className="text-xs text-slate-500 font-mono">
                        Service: <strong className="text-slate-800">{incident.service_name}</strong>
                      </span>
                    )}
                    <span className="text-xs text-slate-500 font-mono ml-auto">
                      {formatTimestamp(incident.created_at)}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-slate-900 pt-1 hover:text-red-600 transition">
                    {incident.title}
                  </h3>
                  {incident.description && (
                    <p className="text-xs text-slate-600">{incident.description}</p>
                  )}

                  {/* AI Root Cause Diagnosis Callout */}
                  {incident.root_cause && (
                    <div className="mt-2.5 rounded-lg border border-red-200 bg-red-50/80 p-3">
                      <div className="flex items-center gap-2 text-red-800 text-xs font-bold mb-1">
                        <Sparkles className="h-3.5 w-3.5 text-red-600" />
                        AI Root Cause Diagnosis:
                      </div>
                      <p className="text-xs text-slate-800 leading-relaxed font-mono">
                        {incident.root_cause}
                      </p>
                      {incident.ai_remediation && (
                        <div className="mt-2 text-xs text-slate-600">
                          <strong className="text-red-800">Recommended Remediation: </strong>
                          {incident.ai_remediation}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Operator Actions */}
                <div className="md:self-center flex-shrink-0 flex items-center gap-2 pt-2 md:pt-0">
                  <button
                    onClick={() => onSelectIncident && onSelectIncident(incident)}
                    className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 border border-slate-300 text-slate-700 hover:text-slate-900 text-xs font-semibold transition shadow-sm"
                  >
                    Details
                  </button>

                  <button
                    onClick={() => handleResolveClick(incident.id)}
                    disabled={resolvingId === incident.id}
                    className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 border border-red-600 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-sm shadow-red-500/20 disabled:opacity-50"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {resolvingId === incident.id ? 'Resolving...' : 'Resolve'}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
