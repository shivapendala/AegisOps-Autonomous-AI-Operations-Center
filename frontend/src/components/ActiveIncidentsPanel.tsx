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
        <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-red-500/10 text-red-400 border border-red-500/30">
          CRITICAL
        </span>
      );
    }
    if (s === 'HIGH') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
          HIGH
        </span>
      );
    }
    if (s === 'MEDIUM') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-yellow-500/10 text-yellow-400 border border-yellow-500/30">
          MEDIUM
        </span>
      );
    }
    return (
      <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
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
    <div className="rounded-xl border border-slate-800 bg-[#0e1628] p-5 shadow-lg backdrop-blur-sm space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-800/80">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-red-950/30 border border-red-500/30 text-red-400">
            <AlertOctagon className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-white tracking-wide">Active Incidents Panel</h2>
              <span className="px-2 py-0.5 text-xs font-mono rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {activeIncidents.length} Active
              </span>
            </div>
            <p className="text-xs text-slate-400">Autonomous triage, root cause analysis & mitigation engine</p>
          </div>
        </div>

        <button
          onClick={handleDrillClick}
          disabled={drillPending || loading}
          className="px-3.5 py-1.5 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/30 border border-cyan-500/40 text-cyan-300 hover:text-white text-xs font-semibold flex items-center gap-2 transition self-start sm:self-auto disabled:opacity-50"
        >
          <Bot className="h-4 w-4" />
          {drillPending ? 'Simulating...' : 'Simulate Ops Drill'}
        </button>
      </div>

      {/* Incidents List */}
      {activeIncidents.length === 0 ? (
        <div className="py-10 text-center flex flex-col items-center justify-center space-y-3">
          <div className="p-3 rounded-full bg-emerald-950/30 border border-emerald-500/30 text-emerald-400">
            <ShieldCheck className="h-8 w-8" />
          </div>
          <p className="text-sm font-semibold text-slate-200">No Active Incidents Detected</p>
          <p className="text-xs text-slate-400 max-w-md">
            All services and telemetry metrics are healthy. The AI engine is actively monitoring incoming telemetry streams.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {activeIncidents.map((incident) => (
            <div
              key={incident.id}
              className="rounded-lg border border-slate-800/90 bg-slate-900/60 p-4 transition hover:border-slate-700"
            >
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                <div
                  className="space-y-1.5 flex-1 cursor-pointer"
                  onClick={() => onSelectIncident && onSelectIncident(incident)}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-cyan-400 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-500/30">
                      {incident.id}
                    </span>
                    {renderSeverityBadge(incident.severity)}
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-amber-950/30 text-amber-300 border border-amber-500/30">
                      {incident.status}
                    </span>
                    {incident.service_name && (
                      <span className="text-xs text-slate-400 font-mono">
                        Service: <strong className="text-slate-200">{incident.service_name}</strong>
                      </span>
                    )}
                    <span className="text-xs text-slate-500 font-mono ml-auto">
                      {formatTimestamp(incident.created_at)}
                    </span>
                  </div>

                  <h3 className="text-sm font-semibold text-white pt-1 hover:text-cyan-300 transition">
                    {incident.title}
                  </h3>
                  {incident.description && (
                    <p className="text-xs text-slate-400">{incident.description}</p>
                  )}

                  {/* AI Root Cause Diagnosis Callout */}
                  {incident.root_cause && (
                    <div className="mt-2.5 rounded-lg border border-cyan-500/20 bg-cyan-950/15 p-3">
                      <div className="flex items-center gap-2 text-cyan-300 text-xs font-semibold mb-1">
                        <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                        AI Root Cause Diagnosis:
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed font-mono">
                        {incident.root_cause}
                      </p>
                      {incident.ai_remediation && (
                        <div className="mt-2 text-xs text-slate-400">
                          <strong className="text-slate-300">Recommended Remediation: </strong>
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
                    className="px-3 py-1.5 rounded-lg bg-cyan-950/50 hover:bg-cyan-900/60 border border-cyan-500/30 text-cyan-300 hover:text-white text-xs font-semibold transition"
                  >
                    Details
                  </button>

                  <button
                    onClick={() => handleResolveClick(incident.id)}
                    disabled={resolvingId === incident.id}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 text-emerald-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
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
