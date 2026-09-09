import React, { useState, useMemo } from 'react';
import { CheckCircle2, Search, BellOff, ShieldAlert } from 'lucide-react';
import { Alert } from '../types';

interface ActiveAlertsTableProps {
  alerts: Alert[];
}

export const ActiveAlertsTable: React.FC<ActiveAlertsTableProps> = ({ alerts }) => {
  const [filter, setFilter] = useState<'ALL' | 'ACTIVE' | 'RESOLVED'>('ACTIVE');
  const [search, setSearch] = useState('');

  const filteredAlerts = useMemo(() => {
    return alerts.filter((a) => {
      const matchesFilter =
        filter === 'ALL'
          ? true
          : filter === 'ACTIVE'
          ? a.status.toUpperCase() === 'ACTIVE'
          : a.status.toUpperCase() === 'RESOLVED';

      const matchesSearch =
        search.trim() === '' ||
        a.service.toLowerCase().includes(search.toLowerCase()) ||
        a.metric.toLowerCase().includes(search.toLowerCase()) ||
        a.message.toLowerCase().includes(search.toLowerCase());

      return matchesFilter && matchesSearch;
    });
  }, [alerts, filter, search]);

  const activeCount = alerts.filter((a) => a.status.toUpperCase() === 'ACTIVE').length;

  const renderSeverityBadge = (severity: string) => {
    const s = severity.toUpperCase();
    if (s === 'CRITICAL') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-red-500/10 text-red-400 border border-red-500/30">
          <span className="h-1.5 w-1.5 rounded-full bg-red-400 mr-1.5 animate-pulse" />
          CRITICAL
        </span>
      );
    }
    if (s === 'WARNING' || s === 'HIGH') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-400 mr-1.5" />
          WARNING
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
        INFO
      </span>
    );
  };

  const renderStatusBadge = (status: string) => {
    const st = status.toUpperCase();
    if (st === 'ACTIVE') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-red-950/40 text-red-400 border border-red-500/40">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500 mr-1.5 animate-ping" />
          ACTIVE
        </span>
      );
    }
    if (st === 'RESOLVED') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-emerald-950/40 text-emerald-400 border border-emerald-500/40">
          <CheckCircle2 className="h-3 w-3 mr-1 text-emerald-400" />
          RESOLVED
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-slate-800 text-slate-300 border border-slate-700">
        {status}
      </span>
    );
  };

  const formatTime = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
        ' ' +
        d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return ts;
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0e1628] shadow-lg backdrop-blur-sm overflow-hidden">
      {/* Header with Search and Filter Controls */}
      <div className="p-4 sm:p-5 border-b border-slate-800/80 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-red-950/30 border border-red-500/30 text-red-400">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-white tracking-wide">Active Alerts Table</h2>
              {activeCount > 0 && (
                <span className="px-2 py-0.5 text-xs font-mono font-bold rounded-full bg-red-500/20 text-red-300 border border-red-500/30">
                  {activeCount} Active
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">Real-time threshold breaches & operational alarms</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Search bar */}
          <div className="relative">
            <Search className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter service/metric..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs bg-slate-900 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Filter Pills */}
          <div className="flex items-center bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setFilter('ACTIVE')}
              className={`px-2.5 py-1 rounded-md font-medium transition ${
                filter === 'ACTIVE'
                  ? 'bg-red-500/20 text-red-300 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Active ({activeCount})
            </button>
            <button
              onClick={() => setFilter('ALL')}
              className={`px-2.5 py-1 rounded-md font-medium transition ${
                filter === 'ALL'
                  ? 'bg-cyan-500/20 text-cyan-300 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All ({alerts.length})
            </button>
            <button
              onClick={() => setFilter('RESOLVED')}
              className={`px-2.5 py-1 rounded-md font-medium transition ${
                filter === 'RESOLVED'
                  ? 'bg-emerald-500/20 text-emerald-300 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Resolved
            </button>
          </div>
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#0b1120] text-slate-400 uppercase tracking-wider font-mono border-b border-slate-800">
            <tr>
              <th scope="col" className="px-4 py-3">Time</th>
              <th scope="col" className="px-4 py-3">Service</th>
              <th scope="col" className="px-4 py-3">Metric</th>
              <th scope="col" className="px-4 py-3">Value</th>
              <th scope="col" className="px-4 py-3">Severity</th>
              <th scope="col" className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {filteredAlerts.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <BellOff className="h-6 w-6 text-slate-600" />
                    <p className="text-xs text-slate-400">
                      {filter === 'ACTIVE'
                        ? 'No active alerts detected. All monitored systems operating within nominal thresholds.'
                        : 'No alerts match the selected criteria.'}
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              filteredAlerts.map((alert) => (
                <tr
                  key={alert.id}
                  className={`transition hover:bg-slate-800/30 ${
                    alert.status.toUpperCase() === 'ACTIVE'
                      ? alert.severity.toUpperCase() === 'CRITICAL'
                        ? 'bg-red-950/10'
                        : 'bg-amber-950/5'
                      : ''
                  }`}
                >
                  {/* Column 1: Time */}
                  <td className="px-4 py-3 whitespace-nowrap text-slate-400 font-mono text-[11px]">
                    {formatTime(alert.timestamp)}
                  </td>

                  {/* Column 2: Service */}
                  <td className="px-4 py-3 whitespace-nowrap font-semibold text-slate-200">
                    <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-300">
                      {alert.service}
                    </span>
                  </td>

                  {/* Column 3: Metric */}
                  <td className="px-4 py-3 whitespace-nowrap text-slate-300 uppercase">
                    {alert.metric}
                  </td>

                  {/* Column 4: Value */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="font-bold text-white font-mono">
                      {typeof alert.value === 'number' ? alert.value.toFixed(1) : alert.value}%
                    </span>
                    <span className="text-[10px] text-slate-500 ml-1">
                      (limit: {alert.threshold}%)
                    </span>
                  </td>

                  {/* Column 5: Severity */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    {renderSeverityBadge(alert.severity)}
                  </td>

                  {/* Column 6: Status */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    {renderStatusBadge(alert.status)}
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
