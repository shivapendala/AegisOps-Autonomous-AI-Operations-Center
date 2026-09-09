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
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-red-300 hover:shadow-md">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Total Services</span>
          <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-600">
            <Server className="h-5 w-5" />
          </div>
        </div>
        <div className="flex items-baseline space-x-2 mb-2">
          <span className="text-3xl font-bold tracking-tight text-slate-900">{totalServices}</span>
          <span className="text-xs text-slate-500 font-mono">Cataloged</span>
        </div>
        <div className="mt-3 flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-2.5">
          <span>Tier-1 Critical:</span>
          <span className="font-mono text-red-600 font-bold">{criticalServices} services</span>
        </div>
      </div>

      {/* 2. Healthy Services */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-red-300 hover:shadow-md">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Healthy Services</span>
          <div className="p-2 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-600">
            <CheckCircle2 className="h-5 w-5" />
          </div>
        </div>
        <div className="flex items-baseline space-x-2 mb-2">
          <span className="text-3xl font-bold tracking-tight text-slate-900">{healthyServices}</span>
          <span className="text-xs text-slate-500">/ {totalServices}</span>
          <span
            className={`ml-auto text-xs px-2 py-0.5 rounded font-mono font-bold ${
              healthPercent >= 90
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-amber-50 text-amber-700 border border-amber-200'
            }`}
          >
            {healthPercent}% SLA
          </span>
        </div>
        <div className="mt-3">
          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden border border-slate-200">
            <div
              className="h-1.5 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-500"
              style={{ width: `${healthPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* 3. Active Alerts */}
      <div
        className={`rounded-xl border p-5 shadow-sm transition hover:shadow-md ${
          criticalAlerts > 0
            ? 'border-red-300 bg-red-50/50'
            : activeAlerts.length > 0
            ? 'border-amber-300 bg-amber-50/50'
            : 'border-slate-200 bg-white'
        }`}
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Active Alerts</span>
          <div
            className={`p-2 rounded-lg border ${
              criticalAlerts > 0
                ? 'bg-red-100 border-red-300 text-red-600'
                : 'bg-amber-100 border-amber-300 text-amber-700'
            }`}
          >
            <AlertTriangle className="h-5 w-5" />
          </div>
        </div>
        <div className="flex items-baseline space-x-2 mb-2">
          <span className="text-3xl font-bold tracking-tight text-slate-900">{activeAlerts.length}</span>
          <span className="text-xs text-slate-500">breaches</span>
        </div>
        <div className="mt-3 flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-2.5">
          <span className="flex items-center gap-1 text-red-600 font-mono font-bold">
            <strong>{criticalAlerts}</strong> Critical
          </span>
          <span className="flex items-center gap-1 text-amber-700 font-mono font-medium">
            <strong>{warningAlerts}</strong> Warning
          </span>
        </div>
      </div>

      {/* 4. Active Incidents */}
      <div
        className={`rounded-xl border p-5 shadow-sm transition hover:shadow-md ${
          criticalIncidents > 0
            ? 'border-red-300 bg-red-50/50'
            : activeIncidents.length > 0
            ? 'border-rose-300 bg-rose-50/50'
            : 'border-slate-200 bg-white'
        }`}
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Active Incidents</span>
          <div
            className={`p-2 rounded-lg border ${
              criticalIncidents > 0
                ? 'bg-red-100 border-red-300 text-red-600'
                : 'bg-rose-100 border-rose-300 text-rose-600'
            }`}
          >
            <AlertOctagon className="h-5 w-5" />
          </div>
        </div>
        <div className="flex items-baseline space-x-2 mb-2">
          <span className="text-3xl font-bold tracking-tight text-slate-900">{activeIncidents.length}</span>
          <span className="text-xs text-slate-500 font-mono">Open/Triage</span>
        </div>
        <div className="mt-3 flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-2.5">
          <span>AI Diagnoses:</span>
          <span className="font-mono text-red-700 font-bold">{incidents.length} total logged</span>
        </div>
      </div>
    </div>
  );
};
