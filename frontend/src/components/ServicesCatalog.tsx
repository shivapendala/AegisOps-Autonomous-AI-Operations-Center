import React from 'react';
import { Server, Activity, ArrowUpRight } from 'lucide-react';
import { ServiceItem } from '../types';

interface ServicesCatalogProps {
  services: ServiceItem[];
}

export const ServicesCatalog: React.FC<ServicesCatalogProps> = ({ services }) => {
  const getStatusDot = (status: string) => {
    switch (status.toUpperCase()) {
      case 'HEALTHY':
        return 'bg-emerald-400';
      case 'DEGRADED':
        return 'bg-amber-400';
      default:
        return 'bg-red-400';
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0e1628] p-5 shadow-lg backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white tracking-wide flex items-center gap-2">
            <Server className="h-4 w-4 text-cyan-400" />
            Monitored Infrastructure Services
          </h3>
          <p className="text-xs text-slate-400">
            Real-time health status and availability state
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Activity className="h-3.5 w-3.5 text-emerald-400" />
          <span>{services.filter((s) => s.status === 'HEALTHY').length}/{services.length} Healthy</span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {services.map((svc) => (
          <div
            key={svc.id}
            className="p-3.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition"
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-semibold text-xs text-white truncate">{svc.name}</span>
              <span className="flex items-center gap-1.5 text-[10px] font-mono font-medium">
                <span className={`h-2 w-2 rounded-full ${getStatusDot(svc.status)}`}></span>
                <span className="text-slate-300">{svc.status}</span>
              </span>
            </div>
            <p className="text-[11px] text-slate-400 line-clamp-1">{svc.description || 'Infrastructure component'}</p>
            <div className="mt-2.5 flex items-center justify-between text-[10px] text-slate-500 font-mono">
              <span className="px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700/50">
                {svc.tier}
              </span>
              {svc.endpoint_url && (
                <span className="flex items-center gap-0.5 text-cyan-400 hover:text-cyan-300">
                  <span>Endpoint</span>
                  <ArrowUpRight className="h-3 w-3" />
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
