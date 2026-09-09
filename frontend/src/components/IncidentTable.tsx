import React from 'react';
import { AlertTriangle, CheckCircle2, Bot, Clock } from 'lucide-react';
import { Incident } from '../types';

interface IncidentTableProps {
  incidents: Incident[];
  onResolve: (id: string) => void;
  onSimulateDrill: () => void;
  loading: boolean;
}

export const IncidentTable: React.FC<IncidentTableProps> = ({
  incidents,
  onResolve,
  onSimulateDrill,
  loading,
}) => {
  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'HIGH':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'MEDIUM':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
      default:
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'RESOLVED':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'INVESTIGATING':
        return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
      default:
        return 'bg-red-500/10 text-red-400 border-red-500/30';
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0e1628] p-5 shadow-lg backdrop-blur-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white tracking-wide flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            Autonomous Operations Incident Triage
          </h3>
          <p className="text-xs text-slate-400">
            Machine-detected anomalies evaluated by AI Root Cause Analysis engine
          </p>
        </div>
        <button
          onClick={onSimulateDrill}
          disabled={loading}
          className="px-3 py-1.5 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/30 border border-cyan-500/40 text-cyan-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition self-start sm:self-auto"
        >
          <Bot className="h-3.5 w-3.5" /> Trigger Operational Drill
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-slate-800 text-slate-400 font-mono uppercase text-[10px]">
            <tr>
              <th className="py-2.5 px-3">Incident ID</th>
              <th className="py-2.5 px-3">Severity</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3">Incident Title & AI Root Cause</th>
              <th className="py-2.5 px-3">Timestamp</th>
              <th className="py-2.5 px-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {incidents.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500">
                  No active incidents detected. Autopilot monitoring telemetry.
                </td>
              </tr>
            ) : (
              incidents.map((incident) => (
                <tr key={incident.id} className="hover:bg-slate-850/50 transition">
                  <td className="py-3 px-3 font-mono font-medium text-cyan-400">
                    {incident.id}
                  </td>
                  <td className="py-3 px-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded border text-[10px] font-bold ${getSeverityBadge(
                        incident.severity
                      )}`}
                    >
                      {incident.severity}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded border text-[10px] font-medium ${getStatusBadge(
                        incident.status
                      )}`}
                    >
                      {incident.status}
                    </span>
                  </td>
                  <td className="py-3 px-3 max-w-md">
                    <div className="font-medium text-white">{incident.title}</div>
                    {incident.root_cause && (
                      <div className="text-[11px] text-slate-400 mt-1 flex items-start gap-1">
                        <span className="text-cyan-400 font-semibold shrink-0">AI Diagnosis:</span>
                        <span className="truncate">{incident.root_cause}</span>
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-3 text-slate-400 whitespace-nowrap">
                    <div className="flex items-center gap-1">
                      <Clock className="h-3 w-3 text-slate-500" />
                      {incident.created_at
                        ? new Date(incident.created_at).toLocaleTimeString()
                        : 'Just now'}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-right">
                    {incident.status !== 'RESOLVED' ? (
                      <button
                        onClick={() => onResolve(incident.id)}
                        className="px-2.5 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[11px] font-medium transition flex items-center gap-1 ml-auto"
                      >
                        <CheckCircle2 className="h-3 w-3" /> Resolve
                      </button>
                    ) : (
                      <span className="text-slate-500 text-[11px] italic">Mitigated</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
