import React from 'react';
import { Shield, Activity, Wifi, WifiOff, RefreshCw, AlertTriangle } from 'lucide-react';
import { ConnectionState, HealthStatus } from '../types';

interface NavbarProps {
  health: HealthStatus | null;
  connectionState: ConnectionState;
  reconnectDelay?: number;
  onRefresh: () => void;
  loading: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  connectionState,
  reconnectDelay,
  onRefresh,
  loading,
}) => {
  const renderConnectionBadge = () => {
    switch (connectionState) {
      case 'connected':
        return (
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-emerald-500/30 text-xs shadow-sm shadow-emerald-500/10">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-emerald-400 font-medium flex items-center gap-1.5 font-mono">
              <Wifi className="h-3.5 w-3.5" /> LIVE MONITOR (WS)
            </span>
          </div>
        );
      case 'reconnecting':
        return (
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-amber-950/20 border border-amber-500/40 text-xs text-amber-300">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
            </span>
            <span className="font-mono flex items-center gap-1">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
              RECONNECTING {reconnectDelay ? `IN ${(reconnectDelay / 1000).toFixed(0)}s` : ''}...
            </span>
          </div>
        );
      case 'connecting':
        return (
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-blue-950/20 border border-blue-500/40 text-xs text-blue-300">
            <span className="h-2 w-2 rounded-full bg-blue-400 animate-pulse"></span>
            <span className="font-mono">CONNECTING WS...</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-red-950/20 border border-red-500/40 text-xs text-red-300">
            <span className="h-2 w-2 rounded-full bg-red-500"></span>
            <span className="font-medium flex items-center gap-1 font-mono">
              <WifiOff className="h-3.5 w-3.5" /> OFFLINE / DISCONNECTED
            </span>
          </div>
        );
    }
  };

  return (
    <header className="border-b border-slate-800 bg-[#0b1120]/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo & Title */}
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Shield className="h-6 w-6 text-slate-950 stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold tracking-tight text-white">AegisOps</span>
              <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                v{health?.version || '0.1.0'}
              </span>
            </div>
            <p className="text-xs text-slate-400">Autonomous AI Operations Center</p>
          </div>
        </div>

        {/* System Status Indicators & Controls */}
        <div className="flex items-center space-x-4">
          {/* Dynamic WebSocket Connection Status Pill */}
          {renderConnectionBadge()}

          {/* AI Engine Provider Badge */}
          <div className="hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
            <Activity className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-slate-400">AI Engine:</span>
            <span className="text-cyan-300 font-semibold uppercase">{health?.ai_engine?.provider || 'MOCK'}</span>
          </div>

          {/* Manual Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition disabled:opacity-50"
            title="Sync Datastore"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
