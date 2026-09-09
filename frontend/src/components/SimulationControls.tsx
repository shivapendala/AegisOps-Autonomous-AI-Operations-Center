import React from 'react';
import {
  Sparkles,
  Cpu,
  Database,
  CreditCard,
  RotateCcw,
  CheckCircle2,
  Layers,
} from 'lucide-react';

interface SimulationControlsProps {
  activeScenario: string;
  onSelectScenario: (scenario: string) => Promise<void>;
  loading: boolean;
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({
  activeScenario,
  onSelectScenario,
  loading,
}) => {
  const scenarios = [
    {
      id: 'NORMAL',
      label: 'Normal',
      badge: 'Baseline',
      icon: CheckCircle2,
      desc: 'Healthy operational baseline across all services',
      colorClass: 'hover:border-emerald-500/50 hover:bg-emerald-950/20 text-emerald-400',
      activeClass: 'bg-emerald-950/40 border-emerald-500 text-emerald-300 shadow-sm shadow-emerald-500/20',
    },
    {
      id: 'HIGH_CPU',
      label: 'CPU Spike',
      badge: 'Order Svc',
      icon: Cpu,
      desc: 'Order Service CPU overload (>92%) & worker saturation',
      colorClass: 'hover:border-amber-500/50 hover:bg-amber-950/20 text-amber-400',
      activeClass: 'bg-amber-950/40 border-amber-500 text-amber-300 shadow-sm shadow-amber-500/20',
    },
    {
      id: 'DATABASE_OVERLOAD',
      label: 'Database Overload',
      badge: 'PostgreSQL',
      icon: Database,
      desc: 'Connection pool saturation (>95%) & query latency surge',
      colorClass: 'hover:border-orange-500/50 hover:bg-orange-950/20 text-orange-400',
      activeClass: 'bg-orange-950/40 border-orange-500 text-orange-300 shadow-sm shadow-orange-500/20',
    },
    {
      id: 'COMBINED_PAYMENT_FAILURE',
      label: 'Payment Failure',
      badge: 'Cascading / Correlation',
      icon: CreditCard,
      desc: 'Multi-vector failure: CPU 92%, DB 95%, Latency 2.8s, 500s -> ONE Incident',
      colorClass: 'hover:border-rose-500/50 hover:bg-rose-950/20 text-rose-400',
      activeClass: 'bg-rose-950/40 border-rose-500 text-rose-300 shadow-sm shadow-rose-500/20',
    },
    {
      id: 'RECOVER_SYSTEM',
      label: 'Recover System',
      badge: 'Self-Heal',
      icon: RotateCcw,
      desc: 'Auto-recover all services, resolve alerts, restore baseline',
      colorClass: 'hover:border-cyan-500/50 hover:bg-cyan-950/20 text-cyan-400',
      activeClass: 'bg-cyan-950/40 border-cyan-500 text-cyan-300 shadow-sm shadow-cyan-500/20',
    },
  ];

  return (
    <div className="rounded-xl border border-cyan-500/30 bg-gradient-to-r from-[#0a1224] via-[#0f172a] to-[#0a1224] p-4 shadow-xl backdrop-blur-md relative overflow-hidden">
      {/* Background visual highlight */}
      <div className="absolute top-0 right-0 -mt-6 -mr-6 w-32 h-32 bg-cyan-500/10 rounded-full blur-2xl pointer-events-none" />

      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        {/* Left Section: Demo Branding & Active Scenario Tag */}
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 uppercase tracking-wider animate-pulse">
              <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
              DEMO / SIMULATION SYSTEM
            </span>
            <span className="flex items-center gap-1 text-xs text-slate-400 font-mono">
              <Layers className="h-3.5 w-3.5 text-slate-500" />
              Active Scenario:
              <strong className="text-white uppercase ml-1">
                {activeScenario.replace(/_/g, ' ')}
              </strong>
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Interactive drill controls for demonstration. Test real-time telemetry, threshold alerts, and event correlation clustering into unified incidents.
          </p>
        </div>

        {/* Right Section: Interactive Scenario Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {scenarios.map((scen) => {
            const Icon = scen.icon;
            const isActive =
              activeScenario.toUpperCase() === scen.id ||
              (scen.id === 'RECOVER_SYSTEM' && activeScenario.toUpperCase() === 'NORMAL');

            return (
              <button
                key={scen.id}
                onClick={() => onSelectScenario(scen.id)}
                disabled={loading}
                title={scen.desc}
                className={`group flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-semibold transition-all duration-150 disabled:opacity-50 ${
                  isActive
                    ? scen.activeClass
                    : `border-slate-800 bg-slate-900/80 ${scen.colorClass}`
                }`}
              >
                <Icon className={`h-4 w-4 transition-transform group-hover:scale-110 ${isActive ? 'animate-pulse' : ''}`} />
                <span>{scen.label}</span>
                {isActive && (
                  <span className="h-1.5 w-1.5 rounded-full bg-current animate-ping" />
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
