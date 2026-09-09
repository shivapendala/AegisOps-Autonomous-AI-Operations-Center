import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  subtext?: string;
  icon: LucideIcon;
  percentage?: number;
  status?: 'normal' | 'warning' | 'critical';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  subtext,
  icon: Icon,
  percentage,
  status = 'normal',
}) => {
  const getColors = () => {
    switch (status) {
      case 'critical':
        return {
          border: 'border-red-500/30',
          bg: 'bg-red-950/10',
          badge: 'text-red-400 bg-red-500/10 border-red-500/20',
          bar: 'bg-red-500',
          icon: 'text-red-400',
        };
      case 'warning':
        return {
          border: 'border-amber-500/30',
          bg: 'bg-amber-950/10',
          badge: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
          bar: 'bg-amber-500',
          icon: 'text-amber-400',
        };
      default:
        return {
          border: 'border-slate-800',
          bg: 'bg-[#0e1628]',
          badge: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
          bar: 'bg-gradient-to-r from-cyan-500 to-blue-500',
          icon: 'text-cyan-400',
        };
    }
  };

  const colors = getColors();

  return (
    <div className={`rounded-xl border ${colors.border} ${colors.bg} p-5 shadow-lg backdrop-blur-sm transition hover:border-slate-700`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</span>
        <div className={`p-2 rounded-lg bg-slate-900/60 border border-slate-800/80 ${colors.icon}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>

      <div className="flex items-baseline space-x-1 mb-2">
        <span className="text-3xl font-bold tracking-tight text-white">{value}</span>
        {unit && <span className="text-sm font-medium text-slate-400">{unit}</span>}
      </div>

      {percentage !== undefined && (
        <div className="mt-3">
          <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden border border-slate-800">
            <div
              className={`h-1.5 rounded-full transition-all duration-500 ${colors.bar}`}
              style={{ width: `${Math.min(100, Math.max(0, percentage))}%` }}
            />
          </div>
        </div>
      )}

      {subtext && (
        <p className="mt-2.5 text-xs text-slate-400 truncate">{subtext}</p>
      )}
    </div>
  );
};
