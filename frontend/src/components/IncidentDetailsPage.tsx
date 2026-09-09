import React, { useEffect, useState } from 'react';
import {
  ArrowLeft,
  Bot,
  CheckCircle2,
  Lock,
  Clock,
  Check,
  ShieldAlert,
  Play,
  CheckSquare,
  Square,
  RotateCw,
} from 'lucide-react';
import { Incident } from '../types';
import {
  fetchIncidentDetails,
  fetchIncidentEvents,
  fetchIncidentRecommendations,
  investigateIncident,
  resolveIncident,
  closeIncident,
  approveRecommendation,
  executeRecommendation,
} from '../services/api';

interface IncidentDetailsPageProps {
  incidentId: string;
  onBack: () => void;
  onIncidentUpdated?: (updated: Incident) => void;
}

interface EventItem {
  id: number | string;
  time: string;
  metric: string;
  value: string;
  severity: string;
  message?: string;
}

interface ActionItem {
  id: number;
  action: string;
  priority: string;
  status: string;
  checked?: boolean;
}

export const IncidentDetailsPage: React.FC<IncidentDetailsPageProps> = ({
  incidentId,
  onBack,
  onIncidentUpdated,
}) => {
  const [incident, setIncident] = useState<Incident | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [errorNotice, setErrorNotice] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  // Load incident details, events, and recommendations
  const loadIncidentData = async () => {
    setLoading(true);
    try {
      const inc = await fetchIncidentDetails(incidentId);
      setIncident(inc);

      // 1. Load Related Events
      let rawEvents: any[] = [];
      try {
        rawEvents = await fetchIncidentEvents(incidentId);
      } catch {
        rawEvents = inc.events || inc.affected_events || [];
      }

      if (rawEvents && rawEvents.length > 0) {
        const mappedEvents: EventItem[] = rawEvents.map((e, idx) => {
          const rawTime = e.timestamp || e.created_at;
          const timeStr = rawTime
            ? new Date(rawTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            : `10:31:0${idx * 2 + 1}`;

          let metricName = e.metric || e.event_data?.metric || 'System Metric';
          if (metricName.toLowerCase().includes('cpu')) metricName = 'CPU';
          else if (metricName.toLowerCase().includes('db') || metricName.toLowerCase().includes('database')) metricName = 'DB';
          else if (metricName.toLowerCase().includes('latenc')) metricName = 'Latency';
          else if (metricName.toLowerCase().includes('500') || metricName.toLowerCase().includes('error')) metricName = 'HTTP 500';

          let valDisplay = e.value !== undefined ? String(e.value) : '↑';
          if (metricName === 'CPU' && !valDisplay.includes('%')) valDisplay = `${valDisplay}%`;
          if (metricName === 'DB' && !valDisplay.includes('%')) valDisplay = `${valDisplay}%`;
          if (metricName === 'Latency' && !valDisplay.includes('sec') && !valDisplay.includes('s')) valDisplay = `${valDisplay} sec`;
          if (metricName === 'HTTP 500' && !valDisplay.includes('↑') && !valDisplay.includes('%')) valDisplay = `↑ ${valDisplay}%`;

          return {
            id: e.id || idx + 1,
            time: timeStr,
            metric: metricName,
            value: valDisplay,
            severity: (e.severity || 'CRITICAL').toUpperCase(),
            message: e.message || e.description,
          };
        });
        setEvents(mappedEvents);
      } else {
        // Default Step 11 cascade events if none in DB
        setEvents([
          { id: 1, time: '10:31:01', metric: 'CPU', value: '94%', severity: 'CRITICAL' },
          { id: 2, time: '10:31:03', metric: 'DB', value: '96%', severity: 'CRITICAL' },
          { id: 3, time: '10:31:05', metric: 'Latency', value: '2.8 sec', severity: 'HIGH' },
          { id: 4, time: '10:31:07', metric: 'HTTP 500', value: '↑', severity: 'HIGH' },
        ]);
      }

      // 2. Load Recommendations
      let recList: any[] = [];
      try {
        recList = await fetchIncidentRecommendations(incidentId);
      } catch {
        recList = inc.recommendations || [];
      }

      if (recList && recList.length > 0) {
        setActions(
          recList.map((r: any, idx: number) => ({
            id: r.id || idx + 1,
            action: r.action || r.title || r.description || `Action #${idx + 1}`,
            priority: (r.priority || (idx < 2 ? 'HIGH' : 'MEDIUM')).toUpperCase(),
            status: (r.status || 'PENDING').toUpperCase(),
            checked: r.status === 'APPROVED' || r.status === 'EXECUTED',
          }))
        );
      } else {
        // Default Step 10 recommendations
        setActions([
          { id: 1, action: 'Check database connection pool', priority: 'HIGH', status: 'PENDING', checked: false },
          { id: 2, action: 'Inspect long-running queries', priority: 'HIGH', status: 'PENDING', checked: false },
          { id: 3, action: 'Check database CPU and memory', priority: 'MEDIUM', status: 'PENDING', checked: false },
          { id: 4, action: 'Review recent Payment API deployments', priority: 'MEDIUM', status: 'PENDING', checked: false },
        ]);
      }
    } catch (err: any) {
      console.error('Failed to load incident details:', err);
      setErrorNotice(err.message || 'Error loading incident details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidentData();
  }, [incidentId]);

  const handleStartInvestigation = async () => {
    setActionLoading('investigate');
    setErrorNotice(null);
    try {
      const updated = await investigateIncident(incidentId, 'Investigation started from Incident Details Page');
      setIncident(updated);
      if (onIncidentUpdated) onIncidentUpdated(updated);
      setSuccessNotice('AI Investigation initiated successfully. Status updated to INVESTIGATING.');
      await loadIncidentData();
    } catch (err: any) {
      setErrorNotice(err.message || 'Failed to start investigation');
    } finally {
      setActionLoading(null);
    }
  };

  const handleResolveIncident = async () => {
    setActionLoading('resolve');
    setErrorNotice(null);
    try {
      const updated = await resolveIncident(incidentId, 'Resolved by Human Operations Engineer');
      setIncident(updated);
      if (onIncidentUpdated) onIncidentUpdated(updated);
      setSuccessNotice('Incident marked as RESOLVED.');
      await loadIncidentData();
    } catch (err: any) {
      setErrorNotice(err.message || 'Failed to resolve incident');
    } finally {
      setActionLoading(null);
    }
  };

  const handleCloseIncident = async () => {
    setActionLoading('close');
    setErrorNotice(null);
    try {
      const updated = await closeIncident(incidentId, 'Incident closed after remediation and review');
      setIncident(updated);
      if (onIncidentUpdated) onIncidentUpdated(updated);
      setSuccessNotice('Incident marked as CLOSED.');
      await loadIncidentData();
    } catch (err: any) {
      setErrorNotice(err.message || 'Failed to close incident');
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleCheck = async (action: ActionItem) => {
    // If not approved yet, operator approving action
    if (action.status === 'PENDING') {
      try {
        await approveRecommendation(incidentId, action.id, 'Operations Engineer', 'Approved via checklist');
        setActions((prev) =>
          prev.map((a) => (a.id === action.id ? { ...a, status: 'APPROVED', checked: true } : a))
        );
        setSuccessNotice(`Action "${action.action}" APPROVED by operator.`);
      } catch (err: any) {
        setErrorNotice(err.message || 'Failed to approve action');
      }
    }
  };

  const handleExecuteAction = async (action: ActionItem) => {
    try {
      await executeRecommendation(incidentId, action.id, 'Operations Engineer', 'Executed action playbook');
      setActions((prev) =>
        prev.map((a) => (a.id === action.id ? { ...a, status: 'EXECUTED', checked: true } : a))
      );
      setSuccessNotice(`Action "${action.action}" EXECUTED successfully.`);
    } catch (err: any) {
      setErrorNotice(err.message || 'Cannot execute unapproved action. Operator approval is required first.');
    }
  };

  // Extract evidence bullets
  const evidenceList = incident?.evidence && incident.evidence.length > 0
    ? incident.evidence
    : [
        'DB connections reached 96%',
        'API latency increased to 2.8 seconds',
        'HTTP 500 errors increased',
        'Payment requests timed out',
      ];

  const probableCause = incident?.probable_cause || incident?.root_cause || 'Database connection pool exhaustion';
  const confidenceScore = incident?.confidence_score
    ? Math.round(incident.confidence_score <= 1.0 ? incident.confidence_score * 100 : incident.confidence_score)
    : 91;
  const correlationScore = incident?.correlation_score ? Math.round(incident.correlation_score) : 91;

  if (loading && !incident) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="flex items-center space-x-3 text-slate-600 font-mono text-sm">
          <RotateCw className="h-5 w-5 animate-spin text-red-600" />
          <span>Loading Incident #{incidentId}...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center justify-between">
          <button
            onClick={onBack}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-200 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Operations Dashboard</span>
          </button>
          <span className="font-mono text-xs text-slate-500">
            Incident ID: <strong className="text-slate-800">{incident?.id || incidentId}</strong>
          </span>
        </div>

        {/* Notices */}
        {errorNotice && (
          <div className="p-3 bg-red-100 border border-red-300 rounded-lg text-xs font-mono text-red-800 flex items-center justify-between">
            <span>⚠️ {errorNotice}</span>
            <button onClick={() => setErrorNotice(null)} className="font-bold ml-2">×</button>
          </div>
        )}
        {successNotice && (
          <div className="p-3 bg-emerald-100 border border-emerald-300 rounded-lg text-xs font-mono text-emerald-800 flex items-center justify-between">
            <span>✓ {successNotice}</span>
            <button onClick={() => setSuccessNotice(null)} className="font-bold ml-2">×</button>
          </div>
        )}

        {/* ========================================================================= */}
        {/* HEADER CARD: Incident Summary (Exact User Specification)               */}
        {/* ========================================================================= */}
        <div className="rounded-2xl border-2 border-red-200 bg-white p-6 shadow-sm">
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <span className="text-3xl" role="img" aria-label="alert">🚨</span>
              <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                {incident?.title || 'Payment API Degradation'}
              </h1>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3 border-t border-slate-100 font-mono">
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-500 uppercase font-semibold">Severity:</span>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                  (incident?.severity || 'CRITICAL').toUpperCase() === 'CRITICAL'
                    ? 'bg-red-100 text-red-700 border border-red-300'
                    : 'bg-amber-100 text-amber-700 border border-amber-300'
                }`}>
                  {incident?.severity || 'CRITICAL'}
                </span>
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-500 uppercase font-semibold">Status:</span>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                  (incident?.status || 'OPEN').toUpperCase() === 'OPEN'
                    ? 'bg-red-50 text-red-700 border border-red-200'
                    : (incident?.status || 'OPEN').toUpperCase() === 'INVESTIGATING'
                    ? 'bg-amber-50 text-amber-700 border border-amber-200'
                    : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                }`}>
                  {incident?.status || 'OPEN'}
                </span>
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-500 uppercase font-semibold">Correlation Score:</span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-100 text-indigo-800 border border-indigo-200">
                  {correlationScore}%
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* SECTION 1: RELATED EVENTS                                                 */}
        {/* ========================================================================= */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200">
            <h2 className="text-sm font-bold tracking-wider text-slate-800 uppercase font-mono flex items-center gap-2">
              <Clock className="h-4 w-4 text-slate-500" />
              <span>RELATED EVENTS</span>
            </h2>
            <span className="text-xs font-mono text-slate-500">{events.length} Correlated Alerts</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs sm:text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-100">
                  <th className="py-2">TIME</th>
                  <th className="py-2">METRIC</th>
                  <th className="py-2">VALUE</th>
                  <th className="py-2 text-right">SEVERITY</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {events.map((evt) => (
                  <tr key={evt.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-2.5 text-slate-600">{evt.time}</td>
                    <td className="py-2.5 font-bold text-slate-900">{evt.metric}</td>
                    <td className="py-2.5 font-bold text-red-600">{evt.value}</td>
                    <td className="py-2.5 text-right">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        evt.severity === 'CRITICAL'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-amber-100 text-amber-700'
                      }`}>
                        {evt.severity}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* SECTION 2: AI INVESTIGATION                                               */}
        {/* ========================================================================= */}
        <div className="rounded-2xl border border-indigo-200 bg-white p-6 shadow-sm space-y-5">
          <div className="flex items-center justify-between pb-2 border-b border-indigo-100">
            <h2 className="text-sm font-bold tracking-wider text-indigo-900 uppercase font-mono flex items-center gap-2">
              <Bot className="h-4 w-4 text-indigo-600" />
              <span>AI INVESTIGATION</span>
            </h2>
            <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
              Autonomous RCA
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Probable Cause */}
            <div className="space-y-2">
              <h3 className="text-xs font-mono font-semibold text-slate-500 uppercase">Probable Cause:</h3>
              <p className="text-base font-bold text-slate-900 bg-slate-50 p-3 rounded-lg border border-slate-200">
                {probableCause}
              </p>
            </div>

            {/* Confidence Score */}
            <div className="space-y-2">
              <h3 className="text-xs font-mono font-semibold text-slate-500 uppercase">Confidence:</h3>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 flex items-center justify-between">
                <span className="text-2xl font-black text-indigo-600 font-mono">{confidenceScore}%</span>
                <div className="w-32 bg-slate-200 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2.5 rounded-full"
                    style={{ width: `${confidenceScore}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Evidence Checklist */}
          <div className="space-y-2 pt-2">
            <h3 className="text-xs font-mono font-semibold text-slate-500 uppercase">Evidence:</h3>
            <div className="bg-slate-50 rounded-lg p-3 border border-slate-200 space-y-2 font-mono text-xs sm:text-sm">
              {evidenceList.map((item, idx) => (
                <div key={idx} className="flex items-center space-x-2 text-slate-800">
                  <Check className="h-4 w-4 text-emerald-600 shrink-0 font-bold" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* SECTION 3: RECOMMENDED ACTIONS                                            */}
        {/* ========================================================================= */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200">
            <h2 className="text-sm font-bold tracking-wider text-slate-800 uppercase font-mono flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-slate-500" />
              <span>RECOMMENDED ACTIONS</span>
            </h2>
            <span className="text-xs font-mono text-slate-500">Human-in-the-Loop Safe</span>
          </div>

          <div className="space-y-2.5">
            {actions.map((act) => (
              <div
                key={act.id}
                className="flex items-center justify-between p-3 rounded-xl border border-slate-200 hover:border-slate-300 bg-slate-50/60 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <button
                    onClick={() => handleToggleCheck(act)}
                    className="text-slate-400 hover:text-slate-700 transition-colors"
                  >
                    {act.checked ? (
                      <CheckSquare className="h-5 w-5 text-emerald-600" />
                    ) : (
                      <Square className="h-5 w-5" />
                    )}
                  </button>
                  <span className={`text-sm font-medium ${act.status === 'EXECUTED' ? 'line-through text-slate-400' : 'text-slate-800'}`}>
                    {act.action}
                  </span>
                </div>

                <div className="flex items-center space-x-2 font-mono">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-bold ${
                      act.priority === 'HIGH'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-amber-100 text-amber-700'
                    }`}
                  >
                    {act.priority}
                  </span>

                  {act.status === 'PENDING' && (
                    <button
                      onClick={() => handleToggleCheck(act)}
                      className="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold px-2 py-1 rounded border border-indigo-200 transition-colors"
                    >
                      Approve
                    </button>
                  )}

                  {act.status === 'APPROVED' && (
                    <button
                      onClick={() => handleExecuteAction(act)}
                      className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-2.5 py-1 rounded transition-colors"
                    >
                      Execute
                    </button>
                  )}

                  {act.status === 'EXECUTED' && (
                    <span className="text-xs text-emerald-700 font-bold flex items-center gap-1">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Done
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ========================================================================= */}
        {/* SECTION 4: PRIMARY ACTION BUTTONS                                         */}
        {/* ========================================================================= */}
        <div className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-2">
          <button
            onClick={handleStartInvestigation}
            disabled={actionLoading !== null || incident?.status === 'RESOLVED' || incident?.status === 'CLOSED'}
            className="w-full sm:w-auto px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium text-sm rounded-xl shadow-sm transition-colors flex items-center justify-center gap-2"
          >
            {actionLoading === 'investigate' ? (
              <RotateCw className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4 fill-white" />
            )}
            <span>Start Investigation</span>
          </button>

          <button
            onClick={handleResolveIncident}
            disabled={actionLoading !== null || incident?.status === 'RESOLVED' || incident?.status === 'CLOSED'}
            className="w-full sm:w-auto px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-medium text-sm rounded-xl shadow-sm transition-colors flex items-center justify-center gap-2"
          >
            {actionLoading === 'resolve' ? (
              <RotateCw className="h-4 w-4 animate-spin" />
            ) : (
              <CheckCircle2 className="h-4 w-4" />
            )}
            <span>Resolve Incident</span>
          </button>

          <button
            onClick={handleCloseIncident}
            disabled={actionLoading !== null || incident?.status === 'CLOSED'}
            className="w-full sm:w-auto px-5 py-2.5 bg-slate-800 hover:bg-slate-900 disabled:opacity-50 text-white font-medium text-sm rounded-xl shadow-sm transition-colors flex items-center justify-center gap-2"
          >
            {actionLoading === 'close' ? (
              <RotateCw className="h-4 w-4 animate-spin" />
            ) : (
              <Lock className="h-4 w-4" />
            )}
            <span>Close Incident</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default IncidentDetailsPage;
