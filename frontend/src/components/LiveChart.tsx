import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';

interface ChartPoint {
  time: string;
  cpu: number;
  memory: number;
  disk: number;
}

interface LiveChartProps {
  data: ChartPoint[];
  title?: string;
}

export const LiveChart: React.FC<LiveChartProps> = ({
  data,
  title = 'Real-time Telemetry Streams (CPU & Memory)',
}) => {
  return (
    <div className="rounded-xl border border-slate-800 bg-[#0e1628] p-5 shadow-lg backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white tracking-wide">{title}</h3>
          <p className="text-xs text-slate-400">Continuous telemetry timeseries sampled from psutil</p>
        </div>
        <div className="flex items-center space-x-4 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-cyan-400"></span>
            <span className="text-slate-300">CPU %</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-indigo-400"></span>
            <span className="text-slate-300">RAM %</span>
          </div>
        </div>
      </div>

      <div className="h-64 w-full">
        {data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-500 text-sm">
            Awaiting live telemetry data packets...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00f2fe" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#00f2fe" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="memGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2945" opacity={0.6} />
              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} stroke="#64748b" tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0b1120',
                  borderColor: '#1e2945',
                  borderRadius: '0.5rem',
                  fontSize: '12px',
                  color: '#f8fafc',
                }}
              />
              <Area
                type="monotone"
                dataKey="cpu"
                name="CPU Utilization %"
                stroke="#00f2fe"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#cpuGradient)"
                isAnimationActive={false}
              />
              <Area
                type="monotone"
                dataKey="memory"
                name="Memory Utilization %"
                stroke="#6366f1"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#memGradient)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};
