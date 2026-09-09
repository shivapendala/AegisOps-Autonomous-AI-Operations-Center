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
      colorClass: 'hover:border-emerald-400 hover:bg-emerald-50 text-emerald-700',
      activeClass: 'bg-emerald-600 border-emerald-600 text-white shadow-sm shadow-emerald-600/20',
    },
    {
      id: 'HIGH_CPU',
      label: 'CPU Spike',
      badge: 'Order Svc',
      icon: Cpu,
      desc: 'Order Service CPU overload (>92%) & worker saturation',
      colorClass: 'hover:border-amber-400 hover:bg-amber-50 text-amber-700',
      activeClass: 'bg-amber-600 border-amber-600 text-white shadow-sm shadow-amber-600/20',
    },
    {
      id: 'DATABASE_OVERLOAD',
      label: 'Database Overload',
      badge: 'PostgreSQL',
      icon: Database,
      desc: 'Connection pool saturation (>95%) & query latency surge',
      colorClass: 'hover:border-orange-400 hover:bg-orange-50 text-orange-700',
      activeClass: 'bg-orange-600 border-orange-600 text-white shadow-sm shadow-orange-600/20',
    },
    {
      id: 'COMBINED_PAYMENT_FAILURE',
      label: '🔥 Simulate Payment Failure',
      badge: 'Cascading / Correlation',
      icon: CreditCard,
      desc: 'Multi-vector failure: CPU 94%, DB 96%, Latency 2.8s, 500s -> ONE Incident',
      colorClass: 'hover:border-red-400 hover:bg-red-50 text-red-700',
      activeClass: 'bg-red-600 border-red-600 text-white shadow-md shadow-red-600/30',
    },
    {
      id: 'RECOVER_SYSTEM',
      label: 'Recover System',
      badge: 'Self-Heal',
      icon: RotateCcw,
      desc: 'Auto-recover all services, resolve alerts, restore baseline',
      colorClass: 'hover:border-rose-400 hover:bg-rose-50 text-rose-700',
      activeClass: 'bg-rose-600 border-rose-600 text-white shadow-sm shadow-rose-600/20',
    },
  ];

  return (
    <div className="rounded-xl border border-red-200 bg-white p-4 shadow-sm relative overflow-hidden">
      {/* Background visual highlight */}
      <div className="absolute top-0 right-0 -mt-6 -mr-6 w-32 h-32 bg-red-500/5 rounded-full blur-2xl pointer-events-none" />

      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        {/* Left Section: Demo Branding & Active Scenario Tag */}
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono font-bold bg-red-100 text-red-800 border border-red-300 uppercase tracking-wider">
              <Sparkles className="h-3.5 w-3.5 text-red-600" />
              DEMO / SIMULATION SYSTEM
            </span>
            <span className="flex items-center gap-1 text-xs text-slate-600 font-mono">
              <Layers className="h-3.5 w-3.5 text-slate-400" />
              Active Scenario:
              <strong className="text-red-700 uppercase ml-1 font-bold">
                {activeScenario.replace(/_/g, ' ')}
              </strong>
            </span>
          </div>
          <p className="text-xs text-slate-500">
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
                    : `border-slate-200 bg-slate-50 ${scen.colorClass}`
                }`}
              >
                <Icon className={`h-4 w-4 transition-transform group-hover:scale-110 ${isActive ? 'animate-pulse' : ''}`} />
                <span>{scen.label}</span>
                {isActive && (
                  <span className="h-1.5 w-1.5 rounded-full bg-white animate-ping" />
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
