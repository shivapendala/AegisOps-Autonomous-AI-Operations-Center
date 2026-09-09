import React from 'react';
import { AlertCircle, CheckCircle, BellRing, Clock } from 'lucide-react';
import { Alert } from '../types';

interface AlertFeedProps {
  alerts: Alert[];
}

export const AlertFeed: React.FC<AlertFeedProps> = ({ alerts }) => {
  const getSeverityStyle = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return {
          border: 'border-red-500/40',
          bg: 'bg-red-950/20',
          badge: 'bg-red-500/20 text-red-300 border-red-500/40',
          icon: 'text-red-400',
        };
      case 'WARNING':
      case 'HIGH':
        return {
          border: 'border-amber-500/40',
          bg: 'bg-amber-950/20',
          badge: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
          icon: 'text-amber-400',
        };
      default:
        return {
          border: 'border-cyan-500/30',
          bg: 'bg-cyan-950/10',
          badge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
          icon: 'text-cyan-400',
        };
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0e1628] p-5 shadow-lg backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white tracking-wide flex items-center gap-2">
            <BellRing className="h-4 w-4 text-cyan-400 animate-pulse" />
            Live Operational Alerts Stream
          </h3>
          <p className="text-xs text-slate-400">
            Threshold breaches broadcast in real-time over WebSocket
          </p>
        </div>
        <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
          {alerts.filter((a) => a.status === 'ACTIVE').length} Active
        </span>
      </div>

      <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
        {alerts.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-500 flex flex-col items-center gap-2">
            <CheckCircle className="h-6 w-6 text-emerald-500/60" />
            <span>All operating metrics within nominal thresholds. Zero active alerts.</span>
          </div>
        ) : (
          alerts.slice(0, 15).map((alert) => {
            const style = getSeverityStyle(alert.severity);
            const isResolved = alert.status === 'RESOLVED';
            return (
              <div
                key={`${alert.id}-${alert.metric}-${alert.status}`}
                className={`p-3 rounded-lg border ${
                  isResolved ? 'border-slate-800 bg-slate-900/40 opacity-75' : `${style.border} ${style.bg}`
                } transition-all duration-300 flex items-start justify-between gap-3`}
              >
                <div className="flex items-start gap-2.5 min-w-0">
                  <div className="mt-0.5 shrink-0">
                    {isResolved ? (
                      <CheckCircle className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <AlertCircle className={`h-4 w-4 ${style.icon}`} />
                    )}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-semibold text-white truncate">
                        {alert.service}: {alert.metric}
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.2 rounded border font-mono font-bold ${style.badge}`}>
                        {alert.severity}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.2 rounded border font-mono ${
                          isResolved
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : 'bg-red-500/10 text-red-400 border-red-500/20'
                        }`}
                      >
                        {alert.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 mt-1 leading-snug">{alert.message}</p>
                    <div className="flex items-center gap-3 mt-1.5 text-[11px] text-slate-400 font-mono">
                      <span>Value: <strong className="text-white">{alert.value}%</strong></span>
                      <span>Threshold: <strong className="text-slate-300">{alert.threshold}%</strong></span>
                      <span className="flex items-center gap-1 text-slate-500">
                        <Clock className="h-3 w-3" />
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
