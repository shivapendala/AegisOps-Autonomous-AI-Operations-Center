import React, { useState, useMemo } from 'react';
import {
  AlertOctagon,
  Bot,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  Search,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { Incident } from '../types';

export interface IncidentsTableProps {
  incidents: Incident[];
  onSelectIncident: (incident: Incident) => void;
  onResolve?: (id: string) => Promise<void>;
  onSimulateDrill?: () => Promise<void>;
  loading?: boolean;
}

export const IncidentsTable: React.FC<IncidentsTableProps> = ({
  incidents,
  onSelectIncident,
  onResolve,
  onSimulateDrill,
  loading = false,
}) => {
  const [filter, setFilter] = useState<'ALL' | 'OPEN' | 'RESOLVED'>('ALL');
  const [search, setSearch] = useState('');
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [drillPending, setDrillPending] = useState(false);

  // Helper to format service display name
  const getServiceDisplayName = (inc: Incident): string => {
    if (inc.service_name) return inc.service_name;
    if (inc.service) {
      if (inc.service.toLowerCase().includes('payment')) return 'Payment API';
      if (inc.service.toLowerCase().includes('auth')) return 'Auth API';
      if (inc.service.toLowerCase().includes('gateway')) return 'API Gateway';
      if (inc.service.toLowerCase().includes('telemetry')) return 'Telemetry Pipeline';
      return inc.service;
    }
    return 'Payment API';
  };

  // Helper to format ID display (e.g. "101" -> "Incident #101" or "101")
  const formatIncidentId = (id: string | number): { raw: string; displayNum: string; label: string } => {
    const raw = String(id);
    const cleanNum = raw.replace(/^INC-PAY-|^INC-AUTH-|^INC-|^#/, '');
    return {
      raw,
      displayNum: cleanNum || raw,
      label: `Incident #${cleanNum || raw}`,
    };
  };

  const filteredIncidents = useMemo(() => {
    return incidents.filter((inc) => {
      const statusUpper = inc.status.toUpperCase();
      const isResolved = statusUpper === 'RESOLVED' || statusUpper === 'CLOSED';
      const isOpen = statusUpper === 'OPEN' || statusUpper === 'INVESTIGATING';

      const matchesFilter =
        filter === 'ALL' ? true : filter === 'OPEN' ? isOpen : isResolved;

      const svcName = getServiceDisplayName(inc).toLowerCase();
      const idInfo = formatIncidentId(inc.id);
      const query = search.toLowerCase().trim();

      const matchesSearch =
        query === '' ||
        idInfo.raw.toLowerCase().includes(query) ||
        idInfo.displayNum.toLowerCase().includes(query) ||
        svcName.includes(query) ||
        (inc.title && inc.title.toLowerCase().includes(query)) ||
        (inc.severity && inc.severity.toLowerCase().includes(query)) ||
        (inc.status && inc.status.toLowerCase().includes(query)) ||
        (inc.probable_cause && inc.probable_cause.toLowerCase().includes(query)) ||
        (inc.root_cause && inc.root_cause.toLowerCase().includes(query));

      return matchesFilter && matchesSearch;
    });
  }, [incidents, filter, search]);

  const openCount = incidents.filter(
    (i) => i.status.toUpperCase() === 'OPEN' || i.status.toUpperCase() === 'INVESTIGATING'
  ).length;

  const resolvedCount = incidents.filter(
    (i) => i.status.toUpperCase() === 'RESOLVED' || i.status.toUpperCase() === 'CLOSED'
  ).length;

  const handleResolveClick = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!onResolve) return;
    setResolvingId(id);
    try {
      await onResolve(id);
    } finally {
      setResolvingId(null);
    }
  };

  const handleDrillClick = async () => {
    if (!onSimulateDrill) return;
    setDrillPending(true);
    try {
      await onSimulateDrill();
    } finally {
      setDrillPending(false);
    }
  };

  const renderSeverityBadge = (severity: string) => {
    const s = severity.toUpperCase();
    if (s === 'CRITICAL') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-red-100 text-red-700 border border-red-300">
          <span className="h-1.5 w-1.5 rounded-full bg-red-600 mr-1.5 animate-pulse" />
          CRITICAL
        </span>
      );
    }
    if (s === 'HIGH') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-100 text-amber-800 border border-amber-300">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-600 mr-1.5" />
          HIGH
        </span>
      );
    }
    if (s === 'MEDIUM') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-yellow-100 text-yellow-800 border border-yellow-300">
          MEDIUM
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-slate-100 text-slate-700 border border-slate-300">
        LOW
      </span>
    );
  };

  const renderStatusBadge = (status: string) => {
    const st = status.toUpperCase();
    if (st === 'OPEN') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-red-100 text-red-700 border border-red-300">
          <span className="h-1.5 w-1.5 rounded-full bg-red-600 mr-1.5 animate-ping" />
          OPEN
        </span>
      );
    }
    if (st === 'INVESTIGATING') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-blue-100 text-blue-700 border border-blue-300">
          <span className="h-1.5 w-1.5 rounded-full bg-blue-600 mr-1.5" />
          INVESTIGATING
        </span>
      );
    }
    if (st === 'RESOLVED') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-300">
          <CheckCircle2 className="h-3 w-3 mr-1 text-emerald-600" />
          RESOLVED
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-slate-100 text-slate-700 border border-slate-300">
        {status}
      </span>
    );
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden space-y-0">
      {/* Header with Title, Badges, Search & Controls */}
      <div className="p-4 sm:p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-white">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-600">
            <AlertOctagon className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900 tracking-wide">Incidents</h2>
              <span className="px-2 py-0.5 text-xs font-mono font-bold rounded-full bg-red-100 text-red-700 border border-red-300">
                {openCount} Open
              </span>
              <span className="px-2 py-0.5 text-xs font-mono font-bold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                {resolvedCount} Resolved
              </span>
            </div>
            <p className="text-xs text-slate-500">Autonomous correlation, root-cause diagnosis & triage</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Filter Pills */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-medium">
            <button
              onClick={() => setFilter('ALL')}
              className={`px-3 py-1 rounded-md transition ${
                filter === 'ALL'
                  ? 'bg-white text-slate-900 shadow-sm font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All ({incidents.length})
            </button>
            <button
              onClick={() => setFilter('OPEN')}
              className={`px-3 py-1 rounded-md transition ${
                filter === 'OPEN'
                  ? 'bg-white text-red-700 shadow-sm font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Open ({openCount})
            </button>
            <button
              onClick={() => setFilter('RESOLVED')}
              className={`px-3 py-1 rounded-md transition ${
                filter === 'RESOLVED'
                  ? 'bg-white text-emerald-700 shadow-sm font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Resolved ({resolvedCount})
            </button>
          </div>

          {/* Search Box */}
          <div className="relative min-w-[180px]">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search incidents..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-red-500"
            />
          </div>

          {/* Ops Drill Button */}
          {onSimulateDrill && (
            <button
              onClick={handleDrillClick}
              disabled={drillPending || loading}
              className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 border border-red-600 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-sm shadow-red-500/20 disabled:opacity-50"
            >
              <Bot className="h-3.5 w-3.5" />
              {drillPending ? 'Simulating...' : 'Simulate Ops Drill'}
            </button>
          )}
        </div>
      </div>

      {/* Incident Table */}
      {filteredIncidents.length === 0 ? (
        <div className="py-12 text-center flex flex-col items-center justify-center space-y-3">
          <div className="p-3 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600">
            <ShieldCheck className="h-8 w-8" />
          </div>
          <p className="text-sm font-bold text-slate-900">No Incidents Found</p>
          <p className="text-xs text-slate-500 max-w-sm">
            {search
              ? 'No incidents matched your query. Clear search to view all logged incidents.'
              : 'All systems are operating normally without active incidents.'}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-mono uppercase tracking-wider text-slate-500">
                <th className="py-3 px-4 font-semibold">ID</th>
                <th className="py-3 px-4 font-semibold">Service</th>
                <th className="py-3 px-4 font-semibold">Severity</th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold hidden md:table-cell">Diagnosis / Probable Cause</th>
                <th className="py-3 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700 font-sans">
              {filteredIncidents.map((incident) => {
                const idInfo = formatIncidentId(incident.id);
                const svcName = getServiceDisplayName(incident);
                const cause = incident.probable_cause || incident.root_cause || incident.title;
                const isOpen =
                  incident.status.toUpperCase() === 'OPEN' ||
                  incident.status.toUpperCase() === 'INVESTIGATING';

                return (
                  <tr
                    key={incident.id}
                    onClick={() => onSelectIncident(incident)}
                    className="hover:bg-red-50/40 transition cursor-pointer group"
                  >
                    {/* ID */}
                    <td className="py-3.5 px-4 font-mono font-bold whitespace-nowrap">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectIncident(incident);
                        }}
                        className="inline-flex items-center gap-1 text-red-700 bg-red-50 hover:bg-red-100 px-2.5 py-1 rounded-md border border-red-200 transition group-hover:border-red-300 font-bold"
                        title={`Click to open ${idInfo.label}`}
                      >
                        <span>{idInfo.label}</span>
                        <ExternalLink className="h-3 w-3 opacity-60 group-hover:opacity-100" />
                      </button>
                    </td>

                    {/* Service */}
                    <td className="py-3.5 px-4 font-semibold text-slate-900 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-slate-400" />
                        <span>{svcName}</span>
                      </div>
                    </td>

                    {/* Severity */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {renderSeverityBadge(incident.severity)}
                    </td>

                    {/* Status */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {renderStatusBadge(incident.status)}
                    </td>

                    {/* Diagnosis / Probable Cause */}
                    <td className="py-3.5 px-4 hidden md:table-cell text-slate-600 max-w-xs truncate">
                      {incident.probable_cause || incident.root_cause ? (
                        <span className="flex items-center gap-1.5 font-mono text-[11px] text-slate-800">
                          <Sparkles className="h-3 w-3 text-red-600 flex-shrink-0" />
                          <span className="truncate">{cause}</span>
                        </span>
                      ) : (
                        <span className="text-slate-400 font-mono text-[11px]">—</span>
                      )}
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                        {isOpen && onResolve && (
                          <button
                            onClick={(e) => handleResolveClick(e, incident.id)}
                            disabled={resolvingId === incident.id}
                            className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-700 text-xs font-semibold flex items-center gap-1 transition shadow-sm disabled:opacity-50"
                          >
                            <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                            {resolvingId === incident.id ? 'Resolving...' : 'Resolve'}
                          </button>
                        )}
                        <button
                          onClick={() => onSelectIncident(incident)}
                          className="px-2.5 py-1 rounded bg-red-600 hover:bg-red-700 border border-red-600 text-white text-xs font-semibold flex items-center gap-1 transition shadow-sm shadow-red-500/20"
                        >
                          <span>Details</span>
                          <ChevronRight className="h-3 w-3" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
