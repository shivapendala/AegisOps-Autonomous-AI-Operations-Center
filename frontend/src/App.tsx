import React, { useEffect, useState, useCallback } from 'react';
import { Cpu, Server, HardDrive, Layers, AlertOctagon, CheckCircle, Database } from 'lucide-react';
import { Navbar } from './components/Navbar';
import { MetricCard } from './components/MetricCard';
import { LiveChart } from './components/LiveChart';
import { IncidentTable } from './components/IncidentTable';
import {
  fetchHealth,
  fetchCurrentMetrics,
  fetchIncidents,
  resolveIncident,
  triggerManualIncident,
} from './services/api';
import { TelemetrySocket } from './services/websocket';
import { HealthStatus, Incident, SystemTelemetry, AnomalyScore } from './types';

interface ChartPoint {
  time: string;
  cpu: number;
  memory: number;
  disk: number;
}

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [telemetry, setTelemetry] = useState<SystemTelemetry | null>(null);
  const [anomaly, setAnomaly] = useState<AnomalyScore | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [chartData, setChartData] = useState<ChartPoint[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [backendError, setBackendError] = useState<string | null>(null);

  const appendChartPoint = useCallback((t: SystemTelemetry) => {
    const timeLabel = new Date(t.timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    setChartData((prev) => {
      const next = [...prev, { time: timeLabel, cpu: t.cpu_percent, memory: t.memory_percent, disk: t.disk_percent }];
      return next.length > 30 ? next.slice(next.length - 30) : next;
    });
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      setBackendError(null);
      const [h, m, incs] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchCurrentMetrics().catch(() => null),
        fetchIncidents().catch(() => []),
      ]);

      if (h) setHealth(h);
      if (m) {
        setTelemetry(m);
        appendChartPoint(m);
      }
      setIncidents(incs);
    } catch (err: any) {
      setBackendError(err.message || 'Unable to connect to AegisOps Backend');
    } finally {
      setLoading(false);
    }
  }, [appendChartPoint]);

  useEffect(() => {
    loadData();

    // Initialize real-time WebSocket connection
    const socket = new TelemetrySocket(
      undefined,
      (data) => {
        setTelemetry(data.telemetry);
        setAnomaly(data.anomaly);
        appendChartPoint(data.telemetry);
      },
      (connected) => {
        setWsConnected(connected);
      }
    );

    socket.connect();

    return () => {
      socket.disconnect();
    };
  }, [loadData, appendChartPoint]);

  const handleResolveIncident = async (id: string) => {
    try {
      await resolveIncident(id, 'Resolved via Operations Console action');
      await loadData();
    } catch (err) {
      console.error('Error resolving incident:', err);
    }
  };

  const handleSimulateDrill = async () => {
    try {
      await triggerManualIncident(
        'Synthetic Chaos Spike Drill',
        'Simulated stress injection to verify autopilot anomaly response pipeline',
        'HIGH'
      );
      await loadData();
    } catch (err) {
      console.error('Error simulating drill:', err);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col">
      <Navbar
        health={health}
        wsConnected={wsConnected}
        onRefresh={loadData}
        loading={loading}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Backend Connectivity Error Alert */}
        {backendError && (
          <div className="rounded-xl border border-red-500/30 bg-red-950/20 p-4 text-sm text-red-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertOctagon className="h-5 w-5 text-red-400 shrink-0" />
              <span>{backendError}. Verify backend server is running on http://localhost:8000.</span>
            </div>
            <button
              onClick={loadData}
              className="px-3 py-1 rounded bg-red-500/20 hover:bg-red-500/30 text-xs font-semibold text-red-200"
            >
              Retry
            </button>
          </div>
        )}

        {/* Real-time Anomaly Intelligence Banner */}
        {anomaly?.is_anomaly ? (
          <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4 shadow-lg flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400">
                <AlertOctagon className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-amber-300">
                  scikit-learn Anomaly Alert: {anomaly.description}
                </h4>
                <p className="text-xs text-slate-400">
                  Anomaly score: <span className="font-mono text-amber-400">{anomaly.score}</span> | Confidence: {(anomaly.confidence * 100).toFixed(0)}%
                </p>
              </div>
            </div>
            <span className="px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-mono">
              OUTLIER DETECTED
            </span>
          </div>
        ) : (
          <div className="rounded-xl border border-slate-800/80 bg-[#0b1120]/60 p-3.5 px-4 shadow flex items-center justify-between text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-400" />
              <span>
                ML Model Status: <strong className="text-slate-200">IsolationForest Nominal</strong> (Contamination threshold: 0.05)
              </span>
            </div>
            <div className="flex items-center gap-3 font-mono">
              <span>Host: <strong className="text-slate-300">{telemetry?.host_name || 'localhost'}</strong></span>
              <span>DB: <strong className="text-cyan-400">{health?.database || 'Active'}</strong></span>
            </div>
          </div>
        )}

        {/* Telemetry Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="CPU Utilization"
            value={telemetry?.cpu_percent !== undefined ? telemetry.cpu_percent : '--'}
            unit="%"
            icon={Cpu}
            percentage={telemetry?.cpu_percent}
            status={
              telemetry && telemetry.cpu_percent > 85
                ? 'critical'
                : telemetry && telemetry.cpu_percent > 70
                ? 'warning'
                : 'normal'
            }
            subtext="Multi-core Host Processor"
          />

          <MetricCard
            title="Memory Usage"
            value={telemetry?.memory_percent !== undefined ? telemetry.memory_percent : '--'}
            unit="%"
            icon={Server}
            percentage={telemetry?.memory_percent}
            status={
              telemetry && telemetry.memory_percent > 88
                ? 'critical'
                : telemetry && telemetry.memory_percent > 75
                ? 'warning'
                : 'normal'
            }
            subtext={
              telemetry?.memory_used_gb && telemetry?.memory_total_gb
                ? `${telemetry.memory_used_gb} GB of ${telemetry.memory_total_gb} GB`
                : 'Virtual Memory Subsystem'
            }
          />

          <MetricCard
            title="Disk Partition"
            value={telemetry?.disk_percent !== undefined ? telemetry.disk_percent : '--'}
            unit="%"
            icon={HardDrive}
            percentage={telemetry?.disk_percent}
            status={
              telemetry && telemetry.disk_percent > 90
                ? 'critical'
                : telemetry && telemetry.disk_percent > 80
                ? 'warning'
                : 'normal'
            }
            subtext={
              telemetry?.disk_free_gb
                ? `${telemetry.disk_free_gb} GB Free Space`
                : 'Root Partition'
            }
          />

          <MetricCard
            title="Active Processes"
            value={telemetry?.process_count !== undefined ? telemetry.process_count : '--'}
            icon={Layers}
            status="normal"
            subtext={
              telemetry?.network_sent_mb !== undefined
                ? `Net: ↑${telemetry.network_sent_mb}MB ↓${telemetry.network_recv_mb}MB`
                : 'Running OS Task Threads'
            }
          />
        </div>

        {/* Live Recharts Streaming Graph */}
        <LiveChart data={chartData} />

        {/* Incident Management & AI Triage */}
        <IncidentTable
          incidents={incidents}
          onResolve={handleResolveIncident}
          onSimulateDrill={handleSimulateDrill}
          loading={loading}
        />
      </main>

      <footer className="border-t border-slate-800/80 bg-[#070b14] py-4 text-center text-xs text-slate-500">
        AegisOps Autonomous AI Operations Center &copy; 2026. Built with FastAPI, WebSocket, scikit-learn, and React.
      </footer>
    </div>
  );
};

export default App;
