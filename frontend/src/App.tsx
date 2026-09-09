import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Cpu, Server, HardDrive, Layers } from 'lucide-react';
import { Navbar } from './components/Navbar';
import { MetricCard } from './components/MetricCard';
import { LiveChart } from './components/LiveChart';
import { AlertFeed } from './components/AlertFeed';
import { ServicesCatalog } from './components/ServicesCatalog';
import { IncidentTable } from './components/IncidentTable';
import {
  fetchHealth,
  fetchCurrentMetrics,
  fetchAlerts,
  fetchServices,
  fetchIncidents,
  resolveIncident,
  triggerManualIncident,
} from './services/api';
import { MonitoringSocket } from './services/websocket';
import {
  Alert,
  ConnectionState,
  HealthStatus,
  Incident,
  ServiceItem,
  SystemTelemetry,
  WebSocketEvent,
} from './types';

interface ChartPoint {
  time: string;
  cpu: number;
  memory: number;
  disk: number;
}

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [telemetry, setTelemetry] = useState<SystemTelemetry | null>(null);
  const [chartData, setChartData] = useState<ChartPoint[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [services, setServices] = useState<ServiceItem[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting');
  const [reconnectDelay, setReconnectDelay] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [lastEventNotice, setLastEventNotice] = useState<string | null>(null);

  const socketRef = useRef<MonitoringSocket | null>(null);

  const appendChartPoint = useCallback((t: SystemTelemetry) => {
    const timeLabel = new Date(t.timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    setChartData((prev) => {
      const next = [
        ...prev,
        {
          time: timeLabel,
          cpu: t.cpu_percent,
          memory: t.memory_percent,
          disk: t.disk_percent,
        },
      ];
      return next.length > 30 ? next.slice(next.length - 30) : next;
    });
  }, []);

  const handleWebSocketMessage = useCallback(
    (event: WebSocketEvent) => {
      switch (event.type) {
        case 'INITIAL_STATE': {
          const { telemetry: initTelem, active_alerts: initAlerts, services: initSvcs } = event.data;
          if (initTelem) {
            setTelemetry(initTelem);
            appendChartPoint(initTelem);
          }
          if (initAlerts) setAlerts(initAlerts);
          if (initSvcs) setServices(initSvcs);
          setLastEventNotice('Synchronized live state over WebSocket');
          break;
        }

        case 'METRICS_UPDATE': {
          const telem: SystemTelemetry = event.data;
          setTelemetry(telem);
          appendChartPoint(telem);
          break;
        }

        case 'NEW_ALERT': {
          const newAlert: Alert = event.data;
          setAlerts((prev) => {
            const filtered = prev.filter((a) => a.id !== newAlert.id);
            return [newAlert, ...filtered];
          });
          setLastEventNotice(`Alert Triggered: ${newAlert.service} ${newAlert.metric} [${newAlert.severity}]`);
          break;
        }

        case 'ALERT_RESOLVED': {
          const resolved: Alert = event.data;
          setAlerts((prev) =>
            prev.map((a) =>
              a.metric === resolved.metric && a.service === resolved.service
                ? { ...a, status: 'RESOLVED', resolved_at: new Date().toISOString() }
                : a
            )
          );
          setLastEventNotice(`Alert Normalized: ${resolved.metric} on ${resolved.service}`);
          break;
        }

        case 'INCIDENT_UPDATE': {
          const inc: Incident = event.data;
          setIncidents((prev) => {
            const index = prev.findIndex((i) => i.id === inc.id);
            if (index >= 0) {
              const updated = [...prev];
              updated[index] = { ...updated[index], ...inc };
              return updated;
            }
            return [inc, ...prev];
          });
          setLastEventNotice(`Incident Updated: ${inc.id} (${inc.status})`);
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
          setLastEventNotice(`Service Status Changed: ${service_name} -> ${status}`);
          break;
        }

        default:
          break;
      }
    },
    [appendChartPoint]
  );

  const loadInitialData = useCallback(async () => {
    setLoading(true);
    try {
      const [h, t, alts, svcs, incs] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchCurrentMetrics().catch(() => null),
        fetchAlerts().catch(() => []),
        fetchServices().catch(() => []),
        fetchIncidents().catch(() => []),
      ]);

      if (h) setHealth(h);
      if (t) {
        setTelemetry(t);
        appendChartPoint(t);
      }
      setAlerts(alts);
      setServices(svcs);
      setIncidents(incs);
    } catch (err) {
      console.error('Initial data fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [appendChartPoint]);

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
    } catch (err) {
      console.error('Error resolving incident:', err);
    }
  };

  const handleSimulateDrill = async () => {
    try {
      await triggerManualIncident(
        'Operational Stress Drill',
        'Simulated stress drill to test real-time WebSocket dashboard reactivity',
        'HIGH'
      );
    } catch (err) {
      console.error('Error simulating drill:', err);
    }
  };

  // Format uptime cleanly
  const formatUptime = (seconds?: number) => {
    if (!seconds) return '--';
    const d = Math.floor(seconds / (3600 * 24));
    const h = Math.floor((seconds % (3600 * 24)) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (d > 0) return `${d}d ${h}h ${m}m`;
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m ${Math.floor(seconds % 60)}s`;
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col">
      <Navbar
        health={health}
        connectionState={connectionState}
        reconnectDelay={reconnectDelay}
        onRefresh={loadInitialData}
        loading={loading}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Real-time Event Toast / Banner */}
        {lastEventNotice && (
          <div className="rounded-lg border border-cyan-500/30 bg-cyan-950/20 px-4 py-2 text-xs text-cyan-300 flex items-center justify-between shadow-sm animate-fadeIn">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
              </span>
              <span className="font-mono">{lastEventNotice}</span>
            </div>
            <button
              onClick={() => setLastEventNotice(null)}
              className="text-cyan-400 hover:text-cyan-200 text-xs font-mono"
            >
              dismiss
            </button>
          </div>
        )}

        {/* Real-time Hardware Telemetry Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="CPU Utilization"
            value={telemetry?.cpu_percent !== undefined ? telemetry.cpu_percent : '--'}
            unit="%"
            icon={Cpu}
            percentage={telemetry?.cpu_percent}
            status={
              telemetry && telemetry.cpu_percent >= 90
                ? 'critical'
                : telemetry && telemetry.cpu_percent >= 70
                ? 'warning'
                : 'normal'
            }
            subtext="Threshold: Warning 70% | Critical 90%"
          />

          <MetricCard
            title="Memory Usage"
            value={telemetry?.memory_percent !== undefined ? telemetry.memory_percent : '--'}
            unit="%"
            icon={Server}
            percentage={telemetry?.memory_percent}
            status={
              telemetry && telemetry.memory_percent >= 90
                ? 'critical'
                : telemetry && telemetry.memory_percent >= 75
                ? 'warning'
                : 'normal'
            }
            subtext="Threshold: Warning 75% | Critical 90%"
          />

          <MetricCard
            title="Disk Usage"
            value={telemetry?.disk_percent !== undefined ? telemetry.disk_percent : '--'}
            unit="%"
            icon={HardDrive}
            percentage={telemetry?.disk_percent}
            status={
              telemetry && telemetry.disk_percent >= 90
                ? 'critical'
                : telemetry && telemetry.disk_percent >= 80
                ? 'warning'
                : 'normal'
            }
            subtext="Threshold: Warning 80% | Critical 90%"
          />

          <MetricCard
            title="Processes & Uptime"
            value={telemetry?.process_count !== undefined ? telemetry.process_count : '--'}
            unit="tasks"
            icon={Layers}
            status="normal"
            subtext={`Uptime: ${formatUptime(telemetry?.uptime_seconds)}`}
          />
        </div>

        {/* Real-time Streaming Time-series Chart */}
        <LiveChart data={chartData} />

        {/* Live Operational Alerts Feed */}
        <AlertFeed alerts={alerts} />

        {/* Monitored Infrastructure Services */}
        <ServicesCatalog services={services} />

        {/* Real-time Incident Triage Table */}
        <IncidentTable
          incidents={incidents}
          onResolve={handleResolveIncident}
          onSimulateDrill={handleSimulateDrill}
          loading={loading}
        />
      </main>

      <footer className="border-t border-slate-800/80 bg-[#070b14] py-4 text-center text-xs text-slate-500 font-mono">
        AegisOps Autonomous AI Operations Center &copy; 2026. Live Streaming via WebSocket (ws://localhost:8000/ws/monitor).
      </footer>
    </div>
  );
};

export default App;
