import React from 'react';
import { Server, CheckCircle2, AlertTriangle, AlertOctagon } from 'lucide-react';
import { Alert, Incident, ServiceItem } from '../types';

interface SummaryCardsProps {
  services: ServiceItem[];
  alerts: Alert[];
  incidents: Incident[];
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({
  services,
  alerts,
  incidents,
}) => {
  const totalServices = services.length;
  const healthyServices = services.filter((s) => s.status.toUpperCase() === 'HEALTHY').length;
  const criticalServices = services.filter((s) => s.tier.toUpperCase() === 'CRITICAL').length;
  const healthPercent = totalServices > 0 ? Math.round((healthyServices / totalServices) * 100) : 100;

  const activeAlerts = alerts.filter((a) => a.status.toUpperCase() === 'ACTIVE');
  const criticalAlerts = activeAlerts.filter((a) => a.severity.toUpperCase() === 'CRITICAL').length;
  const warningAlerts = activeAlerts.filter((a) => a.severity.toUpperCase() === 'WARNING' || a.severity.toUpperCase() === 'HIGH').length;

  const activeIncidents = incidents.filter(
    (i) => i.status.toUpperCase() === 'OPEN' || i.status.toUpperCase() === 'INVESTIGATING'
  );
  const criticalIncidents = activeIncidents.filter((i) => i.severity.toUpperCase() === 'CRITICAL').length;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. Total Services */}
      <div className="rounded-xl border border-slate-800 bg-[#0e1628] p-5 shadow-lg backdrop-blur-sm transition hover:border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Services</span>
          <div className="p-2 rounded-lg bg-cyan-950/40 border border-cyan-500/30 text-cyan-400">
            <Server className="h-5 w-5" />
          </div>
        </div>
        <div className="flex items-baseline space-x-2 mb-2">
          <span className="text-3xl font-bold tracking-tight text-white">{totalServices}</span>
          <span className="text-xs text-slate-400 font-mono">Cataloged</span>
        </div>
        <div className="mt-3 flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/80 pt-2.5">
          <span>Tier-1 Critical:</span>
          <span className="font-mono text-cyan-300 font-semibold">{criticalServices} services</span>
        </div>
      </div>

      {/* 2. Healthy Services */}
      <div className="rounded-xl border border-slate-800 bg-[#0e1628] p-5 shadow-lg backdrop-blur-sm transition hover:border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Healthy Services</span>
          <div className="p-2 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-emerald-400">
            <CheckCircle2 className="h-5 w-5" />
          </div>
        </div>
        <div className="flex items-baseline space-x-2 mb-2">
          <span className="text-3xl font-bold tracking-tight text-white">{healthyServices}</span>
          <span className="text-xs text-slate-400">/ {totalServices}</span>
          <span
            className={`ml-auto text-xs px-2 py-0.5 rounded font-mono font-bold ${
              healthPercent >= 90
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
            }`}
          >
            {healthPercent}% SLA
          </span>
        </div>
        <div className="mt-3">
          <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden border border-slate-800">
            <div
              className="h-1.5 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all duration-500"
              style={{ width: `${healthPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* 3. Active Alerts */}
      <div
        className={`rounded-xl border p-5 shadow-lg backdrop-blur-sm transition ${
          criticalAlerts > 0
            ? 'border-red-500/40 bg-red-950/10'
            : activeAlerts.length > 0
            ? 'border-amber-500/30 bg-amber-950/10'
            : 'border-slate-800 bg-[#0e1628]'
        }`}
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Active Alerts</span>
          <div
            className={`p-2 rounded-lg border ${
              criticalAlerts > 0
                ? 'bg-red-500/20 border-red-500/40 text-red-400'
                : 'bg-amber-500/20 border-amber-500/40 text-amber-400'
            }`}
          >
            <AlertTriangle className="h-5 w-5" />
          </div>
        </div>
        <div className="flex items-baseline space-x-2 mb-2">
          <span className="text-3xl font-bold tracking-tight text-white">{activeAlerts.length}</span>
          <span className="text-xs text-slate-400">breaches</span>
        </div>
        <div className="mt-3 flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/80 pt-2.5">
          <span className="flex items-center gap-1 text-red-400 font-mono">
            <strong>{criticalAlerts}</strong> Critical
          </span>
          <span className="flex items-center gap-1 text-amber-400 font-mono">
            <strong>{warningAlerts}</strong> Warning
          </span>
        </div>
      </div>

      {/* 4. Active Incidents */}
      <div
        className={`rounded-xl border p-5 shadow-lg backdrop-blur-sm transition ${
          criticalIncidents > 0
            ? 'border-red-500/40 bg-red-950/10'
            : activeIncidents.length > 0
            ? 'border-purple-500/30 bg-purple-950/10'
            : 'border-slate-800 bg-[#0e1628]'
        }`}
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Active Incidents</span>
          <div
            className={`p-2 rounded-lg border ${
              criticalIncidents > 0
                ? 'bg-red-500/20 border-red-500/40 text-red-400'
                : 'bg-purple-500/20 border-purple-500/40 text-purple-400'
            }`}
          >
            <AlertOctagon className="h-5 w-5" />
          </div>
        </div>
        <div className="flex items-baseline space-x-2 mb-2">
          <span className="text-3xl font-bold tracking-tight text-white">{activeIncidents.length}</span>
          <span className="text-xs text-slate-400 font-mono">Open/Triage</span>
        </div>
        <div className="mt-3 flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/80 pt-2.5">
          <span>AI Diagnoses:</span>
          <span className="font-mono text-purple-300 font-semibold">{incidents.length} total logged</span>
        </div>
      </div>
    </div>
  );
};
