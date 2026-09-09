import React, { useState } from 'react';
import {
  X,
  Bot,
  CheckCircle2,
  Lock,
  Clock,
  Sparkles,
  Server,
  Search,
  ShieldAlert,
  Activity,
  Check,
} from 'lucide-react';
import { Incident } from '../types';
import { investigateIncident, resolveIncident, closeIncident } from '../services/api';

interface IncidentDetailsModalProps {
  incident: Incident | null;
  isOpen: boolean;
  onClose: () => void;
  onIncidentUpdated: (updated: Incident) => void;
}

export const IncidentDetailsModal: React.FC<IncidentDetailsModalProps> = ({
  incident,
  isOpen,
  onClose,
  onIncidentUpdated,
}) => {
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'evidence' | 'timeline' | 'alerts'>('overview');

  if (!isOpen || !incident) return null;

  const handleInvestigate = async () => {
    setActionLoading('investigate');
    try {
      const updated = await investigateIncident(incident.id, 'Triage started via Incident Console');
      onIncidentUpdated(updated);
    } catch (err) {
      console.error('Failed to investigate incident:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleResolve = async () => {
    setActionLoading('resolve');
    try {
      const updated = await resolveIncident(incident.id, 'Resolved by SRE Operator');
      onIncidentUpdated(updated);
    } catch (err) {
      console.error('Failed to resolve incident:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleClose = async () => {
    setActionLoading('close');
    try {
      const updated = await closeIncident(incident.id, 'Incident closed after verification');
      onIncidentUpdated(updated);
    } catch (err) {
      console.error('Failed to close incident:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const renderStatusBadge = (st: string) => {
    switch (st.toUpperCase()) {
      case 'OPEN':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-mono font-bold bg-red-950/50 text-red-400 border border-red-500/40">
            <span className="h-2 w-2 rounded-full bg-red-500 mr-2 animate-ping" />
            OPEN
          </span>
        );
      case 'INVESTIGATING':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-mono font-bold bg-amber-950/50 text-amber-300 border border-amber-500/40">
            <span className="h-2 w-2 rounded-full bg-amber-400 mr-2 animate-pulse" />
            INVESTIGATING
          </span>
        );
      case 'RESOLVED':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-950/50 text-emerald-300 border border-emerald-500/40">
            <CheckCircle2 className="h-3.5 w-3.5 mr-1.5 text-emerald-400" />
            RESOLVED
          </span>
        );
      case 'CLOSED':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
            <Lock className="h-3.5 w-3.5 mr-1.5 text-slate-400" />
            CLOSED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
            {st}
          </span>
        );
    }
  };

  const renderSeverityBadge = (sev: string) => {
    switch (sev.toUpperCase()) {
      case 'CRITICAL':
        return (
          <span className="px-2.5 py-1 rounded-md text-xs font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/40">
            CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-2.5 py-1 rounded-md text-xs font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
            HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2.5 py-1 rounded-md text-xs font-mono font-bold bg-yellow-500/20 text-yellow-300 border border-yellow-500/40">
            MEDIUM
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-md text-xs font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
            LOW
          </span>
        );
    }
  };

  // Extract structured AI RCA data if present
  const rcaData = incident.metadata_json?.ai_root_cause_analysis || {};
  const confidenceScore = incident.confidence ?? rcaData.confidence_score ?? 0.91;
  const confidencePercent = Math.round(confidenceScore > 1 ? confidenceScore : confidenceScore * 100);

  const evidenceList: string[] =
    incident.evidence && incident.evidence.length > 0
      ? incident.evidence
      : rcaData.evidence && rcaData.evidence.length > 0
      ? rcaData.evidence
      : [
          'Multiple telemetry metrics crossed operational thresholds.',
          'Correlated alert cascade detected on monitored services.',
        ];

  const recommendedActions: string[] =
    incident.recommended_actions && incident.recommended_actions.length > 0
      ? incident.recommended_actions
      : rcaData.recommended_actions && rcaData.recommended_actions.length > 0
      ? rcaData.recommended_actions
      : incident.recommendations && incident.recommendations.length > 0
      ? incident.recommendations.map((r) => r.description)
      : [
          'Review service resource allocation and database query profiles.',
          'Verify connection pool headroom and worker thread health.',
        ];

  const probableCauseText =
    incident.probable_cause || incident.root_cause || rcaData.probable_root_cause || 'Automated triage in progress.';

  const relatedAlerts = incident.affected_events || [];
  const affectedMetrics = incident.affected_metrics || [];
  const timelineEvents = incident.events || [];

  const formatTimestamp = (ts?: string) => {
    if (!ts) return '--';
    try {
      const d = new Date(ts);
      return (
        d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
        ' ' +
        d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
      );
    } catch {
      return ts;
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 sm:p-6 animate-fadeIn">
      <div className="relative w-full max-w-4xl rounded-2xl border border-slate-800 bg-[#0b1222] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-5 sm:p-6 border-b border-slate-800/80 bg-slate-900/50 flex items-start justify-between gap-4">
          <div className="space-y-1.5 flex-1">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="font-mono text-xs font-bold text-cyan-400 bg-cyan-950/50 px-2.5 py-1 rounded-md border border-cyan-500/30">
                {incident.id}
              </span>
              {renderStatusBadge(incident.status)}
              {renderSeverityBadge(incident.severity)}
              <span className="text-xs px-2.5 py-1 rounded-md font-mono bg-purple-950/40 text-purple-300 border border-purple-500/30">
                Correlation: {Math.round(incident.correlation_score || 100)}%
              </span>
            </div>

            {/* Field 1: Incident Title */}
            <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight pt-1">
              {incident.title}
            </h1>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1 font-mono">
              <span className="flex items-center gap-1.5">
                <Server className="h-3.5 w-3.5 text-cyan-400" />
                Service: <strong className="text-slate-200">{incident.service || incident.service_name || 'System'}</strong>
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-slate-400" />
                Opened: <span className="text-slate-300">{formatTimestamp(incident.created_at)}</span>
              </span>
              {incident.resolved_at && (
                <span className="flex items-center gap-1.5 text-emerald-400">
                  <Check className="h-3.5 w-3.5" />
                  Resolved: <span>{formatTimestamp(incident.resolved_at)}</span>
                </span>
              )}
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/60 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 px-6 pt-3 border-b border-slate-800/80 bg-[#090e1a] text-xs font-medium">
          <button
            onClick={() => setActiveTab('overview')}
            className={`pb-3 px-3 font-semibold transition border-b-2 ${
              activeTab === 'overview'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Overview & AI Diagnosis
          </button>
          <button
            onClick={() => setActiveTab('evidence')}
            className={`pb-3 px-3 font-semibold transition border-b-2 ${
              activeTab === 'evidence'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Evidence & Actions ({recommendedActions.length})
          </button>
          <button
            onClick={() => setActiveTab('alerts')}
            className={`pb-3 px-3 font-semibold transition border-b-2 ${
              activeTab === 'alerts'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Related Alerts ({relatedAlerts.length}) & Metrics ({affectedMetrics.length})
          </button>
          <button
            onClick={() => setActiveTab('timeline')}
            className={`pb-3 px-3 font-semibold transition border-b-2 ${
              activeTab === 'timeline'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Timeline ({timelineEvents.length})
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-200">
          {activeTab === 'overview' && (
            <div className="space-y-5">
              {/* AI Root Cause Card */}
              <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-5 shadow-lg relative overflow-hidden">
                <div className="flex items-center justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2 text-cyan-300 font-semibold text-sm tracking-wide">
                    <Sparkles className="h-4 w-4 text-cyan-400" />
                    AI Root Cause Analysis
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400 font-mono">Confidence:</span>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                      {confidencePercent}%
                    </span>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Probable Cause:</span>
                    <p className="text-base font-bold text-white font-mono mt-0.5">{probableCauseText}</p>
                  </div>

                  {rcaData.reasoning_summary && (
                    <div className="text-xs text-slate-300 leading-relaxed font-sans bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                      {rcaData.reasoning_summary}
                    </div>
                  )}

                  {incident.impact_summary && (
                    <div className="text-xs text-slate-400 border-t border-cyan-500/20 pt-2">
                      <strong className="text-slate-300">Impact Summary: </strong>
                      {incident.impact_summary}
                    </div>
                  )}
                </div>
              </div>

              {/* Quick Vitals Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="rounded-lg bg-slate-900/60 border border-slate-800 p-3.5">
                  <div className="text-xs text-slate-400 font-mono mb-1">Target Service</div>
                  <div className="text-sm font-bold text-white">{incident.service || incident.service_name || 'System'}</div>
                </div>
                <div className="rounded-lg bg-slate-900/60 border border-slate-800 p-3.5">
                  <div className="text-xs text-slate-400 font-mono mb-1">Correlation Score</div>
                  <div className="text-sm font-bold text-purple-400 font-mono">
                    {Math.round(incident.correlation_score || 100)} / 100
                  </div>
                </div>
                <div className="rounded-lg bg-slate-900/60 border border-slate-800 p-3.5">
                  <div className="text-xs text-slate-400 font-mono mb-1">Affected Metrics</div>
                  <div className="text-sm font-bold text-cyan-300 font-mono">
                    {affectedMetrics.length} metrics
                  </div>
                </div>
              </div>

              {/* Affected Metrics Tags */}
              {affectedMetrics.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Correlated Metric Streams</h3>
                  <div className="flex flex-wrap gap-2">
                    {affectedMetrics.map((m, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-cyan-300 flex items-center gap-1.5"
                      >
                        <Activity className="h-3 w-3 text-cyan-400" />
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'evidence' && (
            <div className="space-y-6">
              {/* Evidence Section */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Search className="h-4 w-4 text-cyan-400" />
                  <h3 className="text-sm font-semibold text-white">Diagnostic Evidence Points</h3>
                </div>
                <div className="space-y-2">
                  {evidenceList.map((ev, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-lg bg-slate-900/70 border border-slate-800/90 text-xs text-slate-200 font-mono flex items-start gap-2.5"
                    >
                      <span className="h-2 w-2 rounded-full bg-cyan-400 mt-1.5 flex-shrink-0" />
                      <span>{ev}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recommended Actions Section */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  <h3 className="text-sm font-semibold text-white">Recommended Remediation Actions</h3>
                </div>
                <div className="space-y-2">
                  {recommendedActions.map((act, i) => (
                    <div
                      key={i}
                      className="p-3.5 rounded-lg bg-slate-900/70 border border-emerald-500/20 text-xs text-slate-200 flex items-start gap-3"
                    >
                      <span className="flex-shrink-0 px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 text-[10px] font-mono font-bold border border-emerald-500/30">
                        ACTION #{i + 1}
                      </span>
                      <span className="text-slate-100 font-medium">{act}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'alerts' && (
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="h-4 w-4 text-amber-400" />
                  <h3 className="text-sm font-semibold text-white">Correlated Operational Alerts</h3>
                </div>
                <span className="text-xs text-slate-400 font-mono">{relatedAlerts.length} grouped alerts</span>
              </div>

              {relatedAlerts.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800">
                  No individual alerts recorded in this incident container.
                </div>
              ) : (
                <div className="space-y-2">
                  {relatedAlerts.map((alt: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2 font-mono text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 font-bold">
                            {alt.service || incident.service}
                          </span>
                          <span className="text-cyan-300 uppercase font-semibold">{alt.metric}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-red-950/50 text-red-400 border border-red-500/30">
                            {alt.severity || 'ALERT'}
                          </span>
                        </div>
                        {alt.message && <div className="text-slate-400 text-[11px]">{alt.message}</div>}
                      </div>

                      <div className="text-right flex items-center sm:flex-col sm:items-end gap-2">
                        <span className="text-white font-bold">
                          Value: {typeof alt.value === 'number' ? alt.value.toFixed(1) : alt.value}
                        </span>
                        {alt.threshold && (
                          <span className="text-slate-500 text-[10px]">Limit: {alt.threshold}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'timeline' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-cyan-400" />
                <h3 className="text-sm font-semibold text-white">Incident Lifecycle Timeline</h3>
              </div>

              {timelineEvents.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800">
                  No lifecycle timeline events recorded yet.
                </div>
              ) : (
                <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[2px] before:bg-slate-800">
                  {timelineEvents.map((evt, idx) => (
                    <div key={idx} className="relative group">
                      <div className="absolute -left-6 top-1 flex items-center justify-center">
                        <div className="h-4 w-4 rounded-full bg-[#0b1222] border-2 border-cyan-500 flex items-center justify-center" />
                      </div>
                      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-white font-mono">{evt.event_type}</span>
                          <span className="text-slate-400 font-mono text-[11px]">
                            {formatTimestamp(evt.created_at)}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300">{evt.description}</p>
                        {evt.actor && (
                          <div className="text-[10px] text-slate-500 font-mono">Actor: {evt.actor}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer: Operator Action Controls */}
        <div className="p-4 sm:p-5 border-t border-slate-800/80 bg-slate-900/50 flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs text-slate-400 font-mono">
            Status: <span className="font-bold text-white">{incident.status}</span>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Action 1: Investigate */}
            {incident.status === 'OPEN' && (
              <button
                onClick={handleInvestigate}
                disabled={actionLoading !== null}
                className="px-3.5 py-1.5 rounded-lg bg-amber-600/20 hover:bg-amber-600/30 border border-amber-500/40 text-amber-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50"
              >
                <Bot className="h-3.5 w-3.5" />
                {actionLoading === 'investigate' ? 'Investigating...' : 'Start Investigation'}
              </button>
            )}

            {/* Action 2: Resolve */}
            {incident.status !== 'RESOLVED' && incident.status !== 'CLOSED' && (
              <button
                onClick={handleResolve}
                disabled={actionLoading !== null}
                className="px-3.5 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                {actionLoading === 'resolve' ? 'Resolving...' : 'Resolve Incident'}
              </button>
            )}

            {/* Action 3: Close */}
            {incident.status !== 'CLOSED' && (
              <button
                onClick={handleClose}
                disabled={actionLoading !== null}
                className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50"
              >
                <Lock className="h-3.5 w-3.5" />
                {actionLoading === 'close' ? 'Closing...' : 'Close Incident'}
              </button>
            )}

            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-medium transition"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
