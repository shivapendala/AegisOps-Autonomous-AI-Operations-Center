import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { Navbar } from './components/Navbar';
import { SummaryCards } from './components/SummaryCards';
import { TelemetryCharts, TelemetryDataPoint } from './components/TelemetryCharts';
import { ActiveAlertsTable } from './components/ActiveAlertsTable';
import { IncidentsTable } from './components/IncidentsTable';
import { RecentEventsTimeline } from './components/RecentEventsTimeline';
import { SystemHealthIndicator } from './components/SystemHealthIndicator';
import { ServicesCatalog } from './components/ServicesCatalog';
import { IncidentDetailsModal } from './components/IncidentDetailsModal';
import { IncidentDetailsPage } from './components/IncidentDetailsPage';
import { SimulationControls } from './components/SimulationControls';
import { SimulatedServicesGrid } from './components/SimulatedServicesGrid';
import {
  fetchHealth,
  fetchCurrentMetrics,
  fetchAlerts,
  fetchServices,
  fetchIncidents,
  fetchIncidentDetails,
  resolveIncident,
  triggerManualIncident,
  fetchSimulationStatus,
  setSimulationScenario,
} from './services/api';
import { MonitoringSocket } from './services/websocket';
import {
  Alert,
  ConnectionState,
  HealthStatus,
  Incident,
  ServiceItem,
  SimulatedService,
  SystemTelemetry,
  TimelineEvent,
  WebSocketEvent,
} from './types';

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [telemetry, setTelemetry] = useState<SystemTelemetry | null>(null);
  const [chartData, setChartData] = useState<TelemetryDataPoint[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [services, setServices] = useState<ServiceItem[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting');
  const [reconnectDelay, setReconnectDelay] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [toastNotice, setToastNotice] = useState<string | null>(null);
  const [activeScenario, setActiveScenario] = useState<string>('NORMAL');
  const [simulatedServices, setSimulatedServices] = useState<SimulatedService[]>([]);
  const [currentPath, setCurrentPath] = useState<string>(
    typeof window !== 'undefined' ? window.location.pathname : '/'
  );

  const socketRef = useRef<MonitoringSocket | null>(null);

  // Synchronize route changes via popstate
  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigateTo = useCallback((path: string) => {
    window.history.pushState(null, '', path);
    setCurrentPath(path);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  // Append incoming telemetry snapshot to rolling chart history
  const appendTelemetryPoint = useCallback((t: SystemTelemetry) => {
    const timeLabel = new Date(t.timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });

    setChartData((prev) => {
      const next: TelemetryDataPoint[] = [
        ...prev,
        {
          time: timeLabel,
          cpu: t.cpu_percent,
          memory: t.memory_percent,
          disk: t.disk_percent,
          netSent: t.network_sent_mb ?? 0,
          netRecv: t.network_recv_mb ?? 0,
        },
      ];
      return next.length > 30 ? next.slice(next.length - 30) : next;
    });
  }, []);

  // Prepend event to the Recent Events timeline
  const addTimelineEvent = useCallback((event: TimelineEvent) => {
    setTimelineEvents((prev) => [event, ...prev].slice(0, 50));
  }, []);

  // Compute live overall system status
  const systemStatus = useMemo((): 'OPERATIONAL' | 'DEGRADED' | 'CRITICAL' => {
    const hasCriticalAlert = alerts.some(
      (a) => a.status.toUpperCase() === 'ACTIVE' && a.severity.toUpperCase() === 'CRITICAL'
    );
    const hasCriticalIncident = incidents.some(
      (i) => i.status.toUpperCase() !== 'RESOLVED' && i.severity.toUpperCase() === 'CRITICAL'
    );
    if (hasCriticalAlert || hasCriticalIncident) return 'CRITICAL';

    const hasWarningAlert = alerts.some(
      (a) => a.status.toUpperCase() === 'ACTIVE' && (a.severity.toUpperCase() === 'WARNING' || a.severity.toUpperCase() === 'HIGH')
    );
    const hasActiveIncident = incidents.some((i) => i.status.toUpperCase() !== 'RESOLVED');
    const hasDegradedService = services.some((s) => s.status.toUpperCase() !== 'HEALTHY');

    if (hasWarningAlert || hasActiveIncident || hasDegradedService) return 'DEGRADED';

    return 'OPERATIONAL';
  }, [alerts, incidents, services]);

  // Handle incoming real-time WebSocket events
  const handleWebSocketMessage = useCallback(
    (event: WebSocketEvent) => {
      switch (event.type) {
        case 'INITIAL_STATE': {
          const { telemetry: initTelem, active_alerts: initAlerts, services: initSvcs } = event.data;
          if (initTelem) {
            setTelemetry(initTelem);
            appendTelemetryPoint(initTelem);
          }
          if (initAlerts) setAlerts(initAlerts);
          if (initSvcs) setServices(initSvcs);
          addTimelineEvent({
            id: `init-${Date.now()}`,
            event_type: 'SYSTEM',
            title: 'Telemetry Stream Initialized',
            description: 'Established live real-time bidirectional WebSocket channel (/ws/monitor)',
            timestamp: new Date().toISOString(),
            actor: 'System Connection Manager',
          });
          break;
        }

        case 'METRICS_UPDATE': {
          const telem: SystemTelemetry = event.data;
          setTelemetry(telem);
          appendTelemetryPoint(telem);
          break;
        }

        case 'new_alert':
        case 'NEW_ALERT': {
          const alertPayload = event.data || event;
          const newAlert: Alert = {
            id: alertPayload.id || alertPayload.alert_id || Date.now(),
            service: alertPayload.service || 'Payment API',
            metric: alertPayload.metric || 'cpu_usage',
            value: alertPayload.value || 0,
            threshold: alertPayload.threshold || 0,
            severity: alertPayload.severity || 'WARNING',
            message: alertPayload.message || 'Telemetry breach observed',
            status: alertPayload.status || 'ACTIVE',
            timestamp: alertPayload.timestamp || new Date().toISOString(),
          };
          setAlerts((prev) => {
            const filtered = prev.filter((a) => String(a.id) !== String(newAlert.id));
            return [newAlert, ...filtered];
          });
          setToastNotice(`🚨 Alert Triggered: ${newAlert.service} ${newAlert.metric} [${newAlert.severity}]`);
          addTimelineEvent({
            id: `alt-${Date.now()}`,
            event_type: 'ALERT',
            title: `Alert: ${newAlert.service} ${newAlert.metric}`,
            description: newAlert.message,
            severity: newAlert.severity,
            actor: 'psutil Collector & Threshold Engine',
            timestamp: newAlert.timestamp || new Date().toISOString(),
          });
          break;
        }

        case 'alert_resolved':
        case 'ALERT_RESOLVED': {
          const resolved = event.data || event;
          setAlerts((prev) =>
            prev.map((a) =>
              (resolved.id && String(a.id) === String(resolved.id)) ||
              (a.metric === resolved.metric && a.service === resolved.service)
                ? { ...a, status: 'RESOLVED' }
                : a
            )
          );
          setToastNotice(`✅ Alert Normalized: ${resolved.metric} on ${resolved.service}`);
          addTimelineEvent({
            id: `res-${Date.now()}`,
            event_type: 'ALERT',
            title: `Alert Normalized: ${resolved.metric}`,
            description: `Telemetry recovered within nominal threshold limits on ${resolved.service}`,
            severity: 'INFO',
            actor: 'System Threshold Monitor',
            timestamp: resolved.timestamp || new Date().toISOString(),
          });
          break;
        }

        case 'incident_created': {
          const incData = event.data || event;
          const rawId = event.incident_id || incData.incident_id || incData.id;
          const incId = String(rawId || '');
          const severity = incData.severity || event.severity || 'CRITICAL';
          const title = incData.title || event.title || `Incident #${incId}`;

          // Prominently update notification banner without refreshing browser
          if (String(severity).toUpperCase() === 'CRITICAL') {
            setToastNotice('🚨 New Critical Incident');
          } else {
            setToastNotice(`🚨 New Incident: ${title}`);
          }

          if (incData.title && incData.status) {
            const newInc: Incident = {
              id: incId || String(incData.id),
              service_name: incData.service_name || incData.service || 'Payment API',
              service: incData.service || incData.service_name || 'Payment API',
              title: incData.title,
              description: incData.description || '',
              severity: (incData.severity || 'CRITICAL') as any,
              status: incData.status || 'OPEN',
              probable_cause: incData.probable_cause || incData.root_cause,
              root_cause: incData.root_cause || incData.probable_cause,
              correlation_score: incData.correlation_score || 91.0,
              confidence_score: incData.confidence_score || 91.0,
              created_at: incData.created_at || new Date().toISOString(),
              updated_at: incData.updated_at || new Date().toISOString(),
            };
            setIncidents((prev) => {
              const filtered = prev.filter(
                (i) =>
                  String(i.id) !== String(newInc.id) &&
                  String(i.id).replace(/^INC-/, '') !== String(newInc.id).replace(/^INC-/, '')
              );
              return [newInc, ...filtered];
            });
          } else if (incId) {
            fetchIncidentDetails(incId)
              .then((fullInc) => {
                setIncidents((prev) => {
                  const filtered = prev.filter(
                    (i) =>
                      String(i.id) !== String(fullInc.id) &&
                      String(i.id).replace(/^INC-/, '') !== String(fullInc.id).replace(/^INC-/, '')
                  );
                  return [fullInc, ...filtered];
                });
              })
              .catch((err) => console.error('Failed to load incident details for incident_created:', err));
          }

          addTimelineEvent({
            id: `inc-create-${Date.now()}`,
            event_type: 'INCIDENT',
            title: `🚨 Incident #${incId} Created: ${title}`,
            description:
              incData.probable_cause ||
              incData.description ||
              'Autonomous correlation engine synthesized new incident ticket.',
            severity: (String(severity).toUpperCase() as any) || 'CRITICAL',
            actor: 'AegisOps-CorrelationEngine',
            timestamp: new Date().toISOString(),
          });
          break;
        }

        case 'incident_resolved': {
          const incData = event.data || event;
          const rawId = event.incident_id || incData.incident_id || incData.id;
          const incId = String(rawId || '');

          setIncidents((prev) =>
            prev.map((i) => {
              const matches =
                String(i.id) === incId ||
                String(i.id).replace(/^INC-/, '') === incId.replace(/^INC-/, '');
              return matches
                ? { ...i, status: 'RESOLVED', resolved_at: new Date().toISOString() }
                : i;
            })
          );

          setSelectedIncident((curr) =>
            curr &&
            (String(curr.id) === incId ||
              String(curr.id).replace(/^INC-/, '') === incId.replace(/^INC-/, ''))
              ? { ...curr, status: 'RESOLVED', resolved_at: new Date().toISOString() }
              : curr
          );

          setToastNotice(`✅ Incident Resolved: Incident #${incId}`);
          addTimelineEvent({
            id: `inc-res-${Date.now()}`,
            event_type: 'INCIDENT',
            title: `Incident #${incId} Resolved`,
            description: 'Incident ticket closed and service telemetry returned to nominal thresholds.',
            severity: 'INFO',
            actor: 'Operations Console',
            timestamp: new Date().toISOString(),
          });
          break;
        }

        case 'incident_updated':
        case 'INCIDENT_UPDATE': {
          const incData = event.data || event;
          const rawId = event.incident_id || incData.incident_id || incData.id;
          const incId = String(rawId || '');

          if (incData.title && incData.status) {
            const inc: Incident = incData;
            setIncidents((prev) => {
              const index = prev.findIndex(
                (i) =>
                  String(i.id) === String(inc.id) ||
                  String(i.id).replace(/^INC-/, '') === String(inc.id).replace(/^INC-/, '')
              );
              if (index >= 0) {
                const updated = [...prev];
                updated[index] = { ...updated[index], ...inc };
                return updated;
              }
              return [inc, ...prev];
            });
            setSelectedIncident((curr) =>
              curr &&
              (String(curr.id) === String(inc.id) ||
                String(curr.id).replace(/^INC-/, '') === String(inc.id).replace(/^INC-/, ''))
                ? { ...curr, ...inc }
                : curr
            );
          } else if (incId) {
            fetchIncidentDetails(incId)
              .then((fullInc) => {
                setIncidents((prev) => {
                  const index = prev.findIndex(
                    (i) =>
                      String(i.id) === String(fullInc.id) ||
                      String(i.id).replace(/^INC-/, '') === String(fullInc.id).replace(/^INC-/, '')
                  );
                  if (index >= 0) {
                    const updated = [...prev];
                    updated[index] = { ...updated[index], ...fullInc };
                    return updated;
                  }
                  return [fullInc, ...prev];
                });
                setSelectedIncident((curr) =>
                  curr &&
                  (String(curr.id) === String(fullInc.id) ||
                    String(curr.id).replace(/^INC-/, '') === String(fullInc.id).replace(/^INC-/, ''))
                    ? { ...curr, ...fullInc }
                    : curr
                );
              })
              .catch((err) => console.error('Failed to load updated incident:', err));
          }

          setToastNotice(`⚠️ Incident Update: Incident #${incId} [${incData.status || 'UPDATED'}]`);
          addTimelineEvent({
            id: `inc-upd-${Date.now()}`,
            event_type: 'INCIDENT',
            title: `Incident #${incId}: ${incData.title || 'Status Update'}`,
            description:
              incData.root_cause ||
              incData.probable_cause ||
              incData.description ||
              `Status transitioned to ${incData.status}`,
            severity: incData.severity || 'HIGH',
            actor: 'AI Autonomous Operations Engine',
            timestamp: incData.updated_at || incData.created_at || new Date().toISOString(),
          });
          break;
        }

        case 'SERVICE_STATUS_CHANGE': {
          const { service_id, service_name, status } = event.data;
          setServices((prev) =>
            prev.map((s) =>
              s.id === service_id || s.name === service_name
                ? { ...s, status }
                : s
            )
          );
          addTimelineEvent({
            id: `svc-${Date.now()}`,
            event_type: 'SERVICE',
            title: `Service Health Shift: ${service_name}`,
            description: `Status changed to ${status}`,
            actor: 'Health Check Evaluator',
            timestamp: new Date().toISOString(),
          });
          break;
        }

        case 'SIMULATION_UPDATE': {
          const { scenario, snapshots } = event.data;
          if (scenario) setActiveScenario(scenario);
          if (snapshots) setSimulatedServices(snapshots);
          break;
        }

        default:
          break;
      }
    },
    [appendTelemetryPoint, addTimelineEvent]
  );

  // Fetch initial REST snapshot
  const loadInitialData = useCallback(async () => {
    setLoading(true);
    try {
      const [h, t, alts, svcs, incs, simStatus] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchCurrentMetrics().catch(() => null),
        fetchAlerts().catch(() => []),
        fetchServices().catch(() => []),
        fetchIncidents().catch(() => []),
        fetchSimulationStatus().catch(() => null),
      ]);

      if (h) setHealth(h);
      if (t) {
        setTelemetry(t);
        appendTelemetryPoint(t);
      }
      setAlerts(alts);
      setServices(svcs);
      setIncidents(incs);
      if (simStatus) {
        if (simStatus.active_scenario) setActiveScenario(simStatus.active_scenario);
        if (simStatus.services) setSimulatedServices(simStatus.services);
      }

      // Seed initial timeline events from recent incidents & alerts
      const initialEvents: TimelineEvent[] = [];
      incs.forEach((i) => {
        initialEvents.push({
          id: `init-inc-${i.id}`,
          event_type: 'INCIDENT',
          title: `Incident ${i.id}: ${i.title}`,
          description: i.root_cause || i.description || 'Recorded incident',
          severity: i.severity,
          actor: 'AI Root Cause Engine',
          timestamp: i.created_at,
        });
      });
      alts.slice(0, 5).forEach((a) => {
        initialEvents.push({
          id: `init-alt-${a.id}`,
          event_type: 'ALERT',
          title: `Alert on ${a.service}: ${a.metric}`,
          description: a.message,
          severity: a.severity,
          actor: 'psutil Collector',
          timestamp: a.timestamp,
        });
      });
      setTimelineEvents(initialEvents);
    } catch (err) {
      console.error('Initial data fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [appendTelemetryPoint]);

  useEffect(() => {
    loadInitialData();

    // Auto-connect WebSocket to /ws/monitor with exponential reconnect
    const socket = new MonitoringSocket(
      undefined,
      (event) => handleWebSocketMessage(event),
      (state, delay) => {
        setConnectionState(state);
        setReconnectDelay(delay);
      }
    );

    socket.connect();
    socketRef.current = socket;

    return () => {
      socket.disconnect();
    };
  }, [loadInitialData, handleWebSocketMessage]);

  const handleResolveIncident = async (id: string) => {
    try {
      await resolveIncident(id, 'Resolved via Operations Console action');
      setToastNotice(`Incident ${id} marked as resolved`);
    } catch (err) {
      console.error('Error resolving incident:', err);
    }
  };

  const handleSelectIncident = (inc: Incident) => {
    navigateTo(`/incidents/${inc.id}`);
  };

  const handleIncidentUpdated = (updated: Incident) => {
    setIncidents((prev) => {
      const idx = prev.findIndex((i) => i.id === updated.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = { ...next[idx], ...updated };
        return next;
      }
      return [updated, ...prev];
    });
    setSelectedIncident(updated);
    setToastNotice(`Incident ${updated.id} status updated to ${updated.status}`);
  };

  const handleSimulateDrill = async () => {
    try {
      await triggerManualIncident(
        'Operational Stress Drill',
        'Simulated stress drill to test real-time WebSocket dashboard reactivity',
        'HIGH'
      );
      setToastNotice('Simulated operational drill triggered');
    } catch (err) {
      console.error('Error simulating drill:', err);
    }
  };

  const handleSelectScenario = async (scenario: string) => {
    setLoading(true);
    try {
      const res = await setSimulationScenario(scenario);
      if (res && res.active_scenario) {
        setActiveScenario(res.active_scenario);
        if (res.services) setSimulatedServices(res.services);
      }
      setToastNotice(`🎯 Simulation Scenario Activated: ${scenario.replace(/_/g, ' ')}`);
      // Reload alerts, incidents, and services immediately
      await loadInitialData();
    } catch (err) {
      console.error('Error activating simulation scenario:', err);
      setToastNotice('Failed to trigger simulation scenario');
    } finally {
      setLoading(false);
    }
  };

  // Route matching for /incidents/:id
  const incidentRouteMatch = currentPath.match(/^\/incidents\/([^/]+)/);
  if (incidentRouteMatch) {
    const routeIncidentId = incidentRouteMatch[1];
    return (
      <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col font-sans">
        <Navbar
          health={health}
          connectionState={connectionState}
          reconnectDelay={reconnectDelay}
          systemStatus={systemStatus}
          onRefresh={loadInitialData}
          loading={loading}
          onNavigateHome={() => navigateTo('/')}
        />
        <main className="flex-1">
          <IncidentDetailsPage
            incidentId={routeIncidentId}
            onBack={() => navigateTo('/')}
            onIncidentUpdated={handleIncidentUpdated}
          />
        </main>
        <footer className="border-t border-red-100 bg-white py-4 text-center text-xs text-slate-500 font-mono shadow-sm">
          AegisOps Autonomous AI Operations Center &copy; 2026. Real-time Streaming via WebSocket.
        </footer>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col font-sans">
      {/* SECTION 1: Top Navigation (Logo, System Status, WebSocket Status) */}
      <Navbar
        health={health}
        connectionState={connectionState}
        reconnectDelay={reconnectDelay}
        systemStatus={systemStatus}
        onRefresh={loadInitialData}
        loading={loading}
        onNavigateHome={() => navigateTo('/')}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Real-time Event Toast / Notification Banner */}
        {toastNotice && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-xs text-red-800 flex items-center justify-between shadow-sm animate-fadeIn">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
              </span>
              <span className="font-mono font-medium">{toastNotice}</span>
            </div>
            <button
              onClick={() => setToastNotice(null)}
              className="text-red-600 hover:text-red-800 text-xs font-mono ml-4 font-semibold"
            >
              dismiss
            </button>
          </div>
        )}

        {/* DEMO / SIMULATION DRILL CONTROLS FOR PRESENTATION */}
        <SimulationControls
          activeScenario={activeScenario}
          onSelectScenario={handleSelectScenario}
          loading={loading}
        />

        {/* SECTION 2: Summary Cards (Total Services, Healthy Services, Active Alerts, Active Incidents) */}
        <SummaryCards
          services={services}
          alerts={alerts}
          incidents={incidents}
        />

        {/* SECTION 10: System Health Indicator (Live Host Health, Uptime, DB, Processes, AI Engine) */}
        <SystemHealthIndicator
          health={health}
          telemetry={telemetry}
          systemStatus={systemStatus}
        />

        {/* SECTIONS 3, 4, 5, 6: Telemetry Charts (CPU, Memory, Disk, Network) */}
        <TelemetryCharts
          data={chartData}
          currentTelemetry={telemetry}
        />

        {/* SECTION 7: Active Alerts Table (Time, Service, Metric, Value, Severity, Status) */}
        <ActiveAlertsTable
          alerts={alerts}
        />

        {/* SECTION 8: Incidents Table (ID, Service, Severity, Status) */}
        <IncidentsTable
          incidents={incidents}
          onSelectIncident={handleSelectIncident}
          onResolve={handleResolveIncident}
          onSimulateDrill={handleSimulateDrill}
          loading={loading}
        />

        {/* DEMO / SIMULATION: Multi-Vector Simulated Microservices Grid */}
        {simulatedServices.length > 0 && (
          <SimulatedServicesGrid
            services={simulatedServices}
          />
        )}

        {/* Monitored Services Catalog */}
        <ServicesCatalog
          services={services}
        />

        {/* SECTION 9: Recent Events Timeline (Chronological Audit Stream) */}
        <RecentEventsTimeline
          events={timelineEvents}
        />

        {/* Incident Details Console / Modal */}
        <IncidentDetailsModal
          incident={selectedIncident}
          isOpen={selectedIncident !== null}
          onClose={() => setSelectedIncident(null)}
          onIncidentUpdated={handleIncidentUpdated}
        />
      </main>

      <footer className="border-t border-red-100 bg-white py-4 text-center text-xs text-slate-500 font-mono shadow-sm">
        AegisOps Autonomous AI Operations Center &copy; 2026. Real-time Streaming via WebSocket (ws://localhost:8000/ws/monitor).
      </footer>
    </div>
  );
};

export default App;
