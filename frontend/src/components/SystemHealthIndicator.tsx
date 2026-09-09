import React from 'react';
import { ShieldCheck, Database, Clock, Layers, Sparkles } from 'lucide-react';
import { HealthStatus, SystemTelemetry } from '../types';

interface SystemHealthIndicatorProps {
  health: HealthStatus | null;
  telemetry: SystemTelemetry | null;
  systemStatus: 'OPERATIONAL' | 'DEGRADED' | 'CRITICAL';
}

export const SystemHealthIndicator: React.FC<SystemHealthIndicatorProps> = ({
  health,
  telemetry,
  systemStatus,
}) => {
  const formatUptime = (seconds?: number) => {
    if (!seconds) return '--';
    const d = Math.floor(seconds / (3600 * 24));
    const h = Math.floor((seconds % (3600 * 24)) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (d > 0) return `${d}d ${h}h ${m}m ${s}s`;
    if (h > 0) return `${h}h ${m}m ${s}s`;
    return `${m}m ${s}s`;
  };

  const getStatusColor = () => {
    switch (systemStatus) {
      case 'CRITICAL':
        return {
          badge: 'bg-red-100 text-red-700 border-red-300',
          dot: 'bg-red-600',
          text: 'CRITICAL ATTENTION REQUIRED',
        };
      case 'DEGRADED':
        return {
          badge: 'bg-amber-100 text-amber-800 border-amber-300',
          dot: 'bg-amber-500',
          text: 'PERFORMANCE DEGRADED',
        };
      default:
        return {
          badge: 'bg-emerald-50 text-emerald-700 border-emerald-300',
          dot: 'bg-emerald-500',
          text: 'ALL SYSTEMS NOMINAL',
        };
    }
  };

  const statusInfo = getStatusColor();

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        {/* Main Status Badge */}
        <div className="flex items-center space-x-4">
          <div className="relative">
            <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 shadow-sm">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <span className={`absolute -top-1 -right-1 h-3.5 w-3.5 rounded-full ${statusInfo.dot} border-2 border-white animate-pulse`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900 tracking-wide">System Health Indicator</h2>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-mono font-bold border ${statusInfo.badge}`}>
                {statusInfo.text}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Host: <span className="font-mono text-slate-700 font-semibold">{telemetry?.host_name || 'localhost'}</span> · App: <span className="font-mono text-red-700 font-bold">{health?.app_name || 'AegisOps Core'}</span>
            </p>
          </div>
        </div>

        {/* System Vitals Metric Chips */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {/* Uptime */}
          <div className="rounded-lg bg-slate-50 border border-slate-200 p-2.5">
            <div className="flex items-center gap-1.5 text-slate-500 text-[11px] mb-1">
              <Clock className="h-3 w-3 text-red-600" />
              <span>System Uptime</span>
            </div>
            <div className="text-xs font-mono font-bold text-slate-900">
              {formatUptime(telemetry?.uptime_seconds || health?.uptime_seconds)}
            </div>
          </div>

          {/* Database */}
          <div className="rounded-lg bg-slate-50 border border-slate-200 p-2.5">
            <div className="flex items-center gap-1.5 text-slate-500 text-[11px] mb-1">
              <Database className="h-3 w-3 text-emerald-600" />
              <span>Storage Layer</span>
            </div>
            <div className="text-xs font-mono font-bold text-emerald-700 flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              {health?.database?.toUpperCase() || 'POSTGRESQL'}
            </div>
          </div>

          {/* Process Count */}
          <div className="rounded-lg bg-slate-50 border border-slate-200 p-2.5">
            <div className="flex items-center gap-1.5 text-slate-500 text-[11px] mb-1">
              <Layers className="h-3 w-3 text-slate-600" />
              <span>Active Threads</span>
            </div>
            <div className="text-xs font-mono font-bold text-slate-900">
              {telemetry?.process_count ? `${telemetry.process_count} procs` : '--'}
            </div>
          </div>

          {/* AI Detector */}
          <div className="rounded-lg bg-slate-50 border border-slate-200 p-2.5">
            <div className="flex items-center gap-1.5 text-slate-500 text-[11px] mb-1">
              <Sparkles className="h-3 w-3 text-red-600" />
              <span>AI Engine</span>
            </div>
            <div className="text-xs font-mono font-bold text-red-700">
              {health?.ai_engine?.anomaly_detector || 'IsolationForest'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
