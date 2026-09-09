import React from 'react';
import { History, AlertTriangle, AlertOctagon, RefreshCw, Cpu } from 'lucide-react';
import { TimelineEvent } from '../types';

interface RecentEventsTimelineProps {
  events: TimelineEvent[];
}

export const RecentEventsTimeline: React.FC<RecentEventsTimelineProps> = ({ events }) => {
  const getEventIcon = (type: string, severity?: string) => {
    switch (type) {
      case 'ALERT':
        return severity === 'CRITICAL' ? (
          <AlertOctagon className="h-3.5 w-3.5 text-red-600" />
        ) : (
          <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
        );
      case 'INCIDENT':
        return <AlertOctagon className="h-3.5 w-3.5 text-red-600" />;
      case 'SERVICE':
        return <RefreshCw className="h-3.5 w-3.5 text-red-500" />;
      default:
        return <Cpu className="h-3.5 w-3.5 text-slate-500" />;
    }
  };

  const getEventBadgeColor = (type: string, severity?: string) => {
    if (severity === 'CRITICAL') return 'bg-red-100 text-red-700 border-red-300 font-bold';
    if (severity === 'WARNING' || severity === 'HIGH') return 'bg-amber-100 text-amber-800 border-amber-300 font-bold';
    if (type === 'INCIDENT') return 'bg-red-50 text-red-700 border-red-200 font-bold';
    if (type === 'SERVICE') return 'bg-slate-100 text-slate-700 border-slate-200 font-semibold';
    return 'bg-slate-100 text-slate-700 border-slate-200 font-semibold';
  };

  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return ts;
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-200">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-600">
            <History className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-wide">Recent Events Timeline</h2>
            <p className="text-xs text-slate-500">Chronological telemetry audit trail and operator event log</p>
          </div>
        </div>
        <span className="text-xs text-slate-500 font-mono">
          {events.length} events recorded
        </span>
      </div>

      {events.length === 0 ? (
        <div className="py-8 text-center text-slate-400 text-xs">
          No operational events logged yet. Listening to WebSocket stream...
        </div>
      ) : (
        <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[2px] before:bg-red-200">
          {events.slice(0, 15).map((evt, idx) => (
            <div key={evt.id || idx} className="relative group">
              {/* Timeline marker */}
              <div className="absolute -left-6 top-1 flex items-center justify-center">
                <div className="h-4 w-4 rounded-full bg-white border-2 border-red-500 flex items-center justify-center shadow-sm">
                  {idx === 0 && (
                    <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-ping" />
                  )}
                </div>
              </div>

              {/* Event card */}
              <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-3 hover:bg-red-50/30 hover:border-red-200 transition shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2">
                    <span className="p-1 rounded bg-white border border-slate-200">
                      {getEventIcon(evt.event_type, evt.severity)}
                    </span>
                    <span className="text-xs font-bold text-slate-900">{evt.title}</span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-mono border ${getEventBadgeColor(
                        evt.event_type,
                        evt.severity
                      )}`}
                    >
                      {evt.event_type}
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500">
                    {formatTimestamp(evt.timestamp)}
                  </span>
                </div>
                <p className="text-xs text-slate-700 font-mono pl-6">{evt.description}</p>
                {evt.actor && (
                  <div className="mt-1 pl-6 text-[10px] text-slate-400 font-mono">
                    Actor: <span className="text-slate-600">{evt.actor}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
