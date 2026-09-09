import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  CartesianGrid,
  Legend,
} from 'recharts';
import { Cpu, Server, HardDrive, Network, Activity } from 'lucide-react';
import { SystemTelemetry } from '../types';

export interface TelemetryDataPoint {
  time: string;
  cpu: number;
  memory: number;
  disk: number;
  netSent: number;
  netRecv: number;
}

interface TelemetryChartsProps {
  data: TelemetryDataPoint[];
  currentTelemetry: SystemTelemetry | null;
}

const CustomTooltip = ({ active, payload, label, unit = '%' }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-2.5 shadow-xl backdrop-blur-md text-xs font-mono">
        <p className="text-slate-500 mb-1 font-semibold">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={`item-${index}`} className="flex items-center justify-between gap-4 py-0.5">
            <span style={{ color: entry.color }} className="flex items-center gap-1.5 font-medium">
              <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: entry.color }} />
              {entry.name}:
            </span>
            <span className="font-bold text-slate-900">
              {typeof entry.value === 'number' ? entry.value.toFixed(1) : entry.value} {unit}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export const TelemetryCharts: React.FC<TelemetryChartsProps> = ({ data, currentTelemetry }) => {
  const latestCpu = currentTelemetry?.cpu_percent ?? (data.length > 0 ? data[data.length - 1].cpu : 0);
  const latestMem = currentTelemetry?.memory_percent ?? (data.length > 0 ? data[data.length - 1].memory : 0);
  const latestDisk = currentTelemetry?.disk_percent ?? (data.length > 0 ? data[data.length - 1].disk : 0);
  const latestNetSent = currentTelemetry?.network_sent_mb ?? (data.length > 0 ? data[data.length - 1].netSent : 0);
  const latestNetRecv = currentTelemetry?.network_recv_mb ?? (data.length > 0 ? data[data.length - 1].netRecv : 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Activity className="h-5 w-5 text-red-600" />
          <h2 className="text-base font-semibold text-slate-900 tracking-wide">Real-time Telemetry Streams</h2>
        </div>
        <span className="text-xs text-slate-500 font-mono flex items-center gap-1.5">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-600"></span>
          </span>
          Sampling rate: 2000ms
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Section 3: CPU Chart */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-600">
                <Cpu className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900">CPU Utilization</h3>
                <p className="text-[11px] text-slate-500 font-mono">Warn: 70% | Crit: 90%</p>
              </div>
            </div>
            <div className="text-right">
              <span
                className={`text-xl font-bold font-mono ${
                  latestCpu >= 90 ? 'text-red-600' : latestCpu >= 70 ? 'text-amber-600' : 'text-red-500'
                }`}
              >
                {latestCpu.toFixed(1)}%
              </span>
              <div className="text-[10px] text-slate-500 font-medium">Current Load</div>
            </div>
          </div>

          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="time" stroke="#94a3b8" tick={{ fontSize: 10 }} tickLine={false} />
                <YAxis stroke="#94a3b8" domain={[0, 100]} tick={{ fontSize: 10 }} tickLine={false} />
                <Tooltip content={<CustomTooltip unit="%" />} />
                <ReferenceLine y={70} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: 'Warn 70%', fill: '#d97706', fontSize: 10, position: 'insideTopLeft' }} />
                <ReferenceLine y={90} stroke="#dc2626" strokeDasharray="3 3" label={{ value: 'Crit 90%', fill: '#dc2626', fontSize: 10, position: 'insideTopLeft' }} />
                <Area
                  type="monotone"
                  dataKey="cpu"
                  name="CPU"
                  stroke="#dc2626"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#cpuGradient)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Section 4: Memory Chart */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-lg bg-rose-50 border border-rose-200 text-rose-600">
                <Server className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900">Memory Usage</h3>
                <p className="text-[11px] text-slate-500 font-mono">Warn: 75% | Crit: 90%</p>
              </div>
            </div>
            <div className="text-right">
              <span
                className={`text-xl font-bold font-mono ${
                  latestMem >= 90 ? 'text-red-600' : latestMem >= 75 ? 'text-amber-600' : 'text-rose-600'
                }`}
              >
                {latestMem.toFixed(1)}%
              </span>
              <div className="text-[10px] text-slate-500 font-medium">
                {currentTelemetry?.memory_used_gb ? `${currentTelemetry.memory_used_gb} GB used` : 'RAM'}
              </div>
            </div>
          </div>

          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="memGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#e11d48" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#e11d48" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="time" stroke="#94a3b8" tick={{ fontSize: 10 }} tickLine={false} />
                <YAxis stroke="#94a3b8" domain={[0, 100]} tick={{ fontSize: 10 }} tickLine={false} />
                <Tooltip content={<CustomTooltip unit="%" />} />
                <ReferenceLine y={75} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: 'Warn 75%', fill: '#d97706', fontSize: 10, position: 'insideTopLeft' }} />
                <ReferenceLine y={90} stroke="#dc2626" strokeDasharray="3 3" label={{ value: 'Crit 90%', fill: '#dc2626', fontSize: 10, position: 'insideTopLeft' }} />
                <Area
                  type="monotone"
                  dataKey="memory"
                  name="Memory"
                  stroke="#e11d48"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#memGradient)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        {/* Section 5: Disk Chart */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-600">
                <HardDrive className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900">Disk Storage</h3>
                <p className="text-[11px] text-slate-500 font-mono">Warn: 80% | Crit: 90%</p>
              </div>
            </div>
            <div className="text-right">
              <span
                className={`text-xl font-bold font-mono ${
                  latestDisk >= 90 ? 'text-red-600' : latestDisk >= 80 ? 'text-amber-600' : 'text-slate-700'
                }`}
              >
                {latestDisk.toFixed(1)}%
              </span>
              <div className="text-[10px] text-slate-500 font-medium">
                {currentTelemetry?.disk_free_gb ? `${currentTelemetry.disk_free_gb} GB free` : 'Volume'}
              </div>
            </div>
          </div>

          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="diskGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#b91c1c" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#b91c1c" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="time" stroke="#94a3b8" tick={{ fontSize: 10 }} tickLine={false} />
                <YAxis stroke="#94a3b8" domain={[0, 100]} tick={{ fontSize: 10 }} tickLine={false} />
                <Tooltip content={<CustomTooltip unit="%" />} />
                <ReferenceLine y={80} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: 'Warn 80%', fill: '#d97706', fontSize: 10, position: 'insideTopLeft' }} />
                <ReferenceLine y={90} stroke="#dc2626" strokeDasharray="3 3" label={{ value: 'Crit 90%', fill: '#dc2626', fontSize: 10, position: 'insideTopLeft' }} />
                <Area
                  type="monotone"
                  dataKey="disk"
                  name="Disk"
                  stroke="#b91c1c"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#diskGradient)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Section 6: Network Chart */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-600">
                <Network className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900">Network I/O</h3>
                <p className="text-[11px] text-slate-500 font-mono">Cumulative Network Traffic</p>
              </div>
            </div>
            <div className="text-right flex items-center gap-3">
              <div>
                <span className="text-xs text-red-600 font-mono font-bold block">↑ {latestNetSent.toFixed(1)} MB</span>
                <span className="text-[10px] text-slate-500 font-medium">Total Sent</span>
              </div>
              <div>
                <span className="text-xs text-slate-700 font-mono font-bold block">↓ {latestNetRecv.toFixed(1)} MB</span>
                <span className="text-[10px] text-slate-500 font-medium">Total Recv</span>
              </div>
            </div>
          </div>

          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="netSentGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="netRecvGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#64748b" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#64748b" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="time" stroke="#94a3b8" tick={{ fontSize: 10 }} tickLine={false} />
                <YAxis stroke="#94a3b8" tick={{ fontSize: 10 }} tickLine={false} />
                <Tooltip content={<CustomTooltip unit="MB" />} />
                <Legend iconSize={8} wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
                <Area
                  type="monotone"
                  dataKey="netSent"
                  name="Sent (MB)"
                  stroke="#ef4444"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#netSentGrad)"
                  isAnimationActive={false}
                />
                <Area
                  type="monotone"
                  dataKey="netRecv"
                  name="Recv (MB)"
                  stroke="#64748b"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#netRecvGrad)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
