import React from 'react';
import { Server, Activity, Clock } from 'lucide-react';
import { SimulatedService } from '../types';

interface SimulatedServicesGridProps {
  services: SimulatedService[];
}

export const SimulatedServicesGrid: React.FC<SimulatedServicesGridProps> = ({ services }) => {
  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'HEALTHY':
        return (
          <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950/40 text-emerald-400 border border-emerald-500/30 font-semibold">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            HEALTHY
          </span>
        );
      case 'DEGRADED':
        return (
          <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-950/40 text-amber-400 border border-amber-500/30 font-semibold">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse"></span>
            DEGRADED
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-rose-950/40 text-rose-400 border border-rose-500/30 font-semibold">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-400 animate-ping"></span>
            CRITICAL
          </span>
        );
    }
  };

  const getMetricColor = (val: number, warnThresh: number, critThresh: number) => {
    if (val >= critThresh) return 'text-rose-400 font-bold';
    if (val >= warnThresh) return 'text-amber-400 font-semibold';
    return 'text-slate-200';
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0e1628] p-5 shadow-lg backdrop-blur-sm space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 border-b border-slate-800/80">
        <div>
          <h3 className="text-sm font-semibold text-white tracking-wide flex items-center gap-2">
            <Server className="h-4 w-4 text-cyan-400" />
            Simulated Microservices Telemetry
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/40 text-cyan-300 border border-cyan-500/30">
              DEMO / SIMULATION
            </span>
          </h3>
          <p className="text-xs text-slate-400">
            Real-time live multi-vector metrics: Latency, Request Rate, Error Rate, CPU, Memory, DB Connections
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
          <Activity className="h-3.5 w-3.5 text-emerald-400" />
          <span>
            {services.filter((s) => s.status === 'HEALTHY').length}/{services.length} Healthy
          </span>
        </div>
      </div>

      {/* 5-Service Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3.5">
        {services.map((svc) => (
          <div
            key={svc.service_name}
            className={`p-4 rounded-xl border transition-all duration-200 flex flex-col justify-between ${
              svc.status === 'CRITICAL'
                ? 'border-rose-500/40 bg-rose-950/10 shadow-lg shadow-rose-950/20'
                : svc.status === 'DEGRADED'
                ? 'border-amber-500/40 bg-amber-950/10'
                : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
            }`}
          >
            {/* Service Top */}
            <div className="space-y-1.5 mb-3">
              <div className="flex items-center justify-between gap-1">
                <span className="font-semibold text-xs text-white truncate" title={svc.service_name}>
                  {svc.service_name}
                </span>
                {getStatusBadge(svc.status)}
              </div>
              <div className="flex items-center gap-1 text-[10px] text-slate-500 font-mono">
                <Clock className="h-3 w-3" />
                <span>Tick: {new Date(svc.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
              </div>
            </div>

            {/* Metrics Breakdown Grid */}
            <div className="grid grid-cols-2 gap-2 text-[11px] font-mono border-t border-slate-800/80 pt-2.5">
              {/* Latency */}
              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-500 block">Latency</span>
                <span className={getMetricColor(svc.latency, 300, 1000)}>
                  {svc.latency >= 1000 ? `${(svc.latency / 1000).toFixed(2)}s` : `${svc.latency.toFixed(0)}ms`}
                </span>
              </div>

              {/* Request Rate */}
              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-500 block">Req Rate</span>
                <span className="text-slate-200">{svc.request_rate.toFixed(0)}/s</span>
              </div>

              {/* Error Rate */}
              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-500 block">Error Rate</span>
                <span className={getMetricColor(svc.error_rate, 2.0, 10.0)}>
                  {svc.error_rate.toFixed(2)}%
                </span>
              </div>

              {/* CPU */}
              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-500 block">CPU</span>
                <span className={getMetricColor(svc.cpu, 70, 90)}>
                  {svc.cpu.toFixed(1)}%
                </span>
              </div>

              {/* Memory */}
              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-500 block">Memory</span>
                <span className={getMetricColor(svc.memory, 75, 90)}>
                  {svc.memory.toFixed(1)}%
                </span>
              </div>

              {/* Database Connections */}
              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-500 block">DB Conns</span>
                <span className={getMetricColor(svc.database_connections, 75, 90)}>
                  {svc.database_connections.toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
