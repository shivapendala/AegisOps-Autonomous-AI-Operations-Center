import React from 'react';
import { Shield, Activity, Wifi, WifiOff, RefreshCw, AlertTriangle, CheckCircle2, AlertOctagon } from 'lucide-react';
import { ConnectionState, HealthStatus } from '../types';

interface NavbarProps {
  health: HealthStatus | null;
  connectionState: ConnectionState;
  reconnectDelay?: number;
  systemStatus: 'OPERATIONAL' | 'DEGRADED' | 'CRITICAL';
  onRefresh: () => void;
  loading: boolean;
  onNavigateHome?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  connectionState,
  reconnectDelay,
  systemStatus,
  onRefresh,
  loading,
  onNavigateHome,
}) => {
  const renderConnectionBadge = () => {
    switch (connectionState) {
      case 'connected':
        return (
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-white border border-red-200 text-xs shadow-sm">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-600"></span>
            </span>
            <span className="text-red-600 font-semibold flex items-center gap-1.5 font-mono">
              <Wifi className="h-3.5 w-3.5" /> LIVE MONITOR (WS)
            </span>
          </div>
        );
      case 'reconnecting':
        return (
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-300 text-xs text-amber-800">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
            </span>
            <span className="font-mono flex items-center gap-1 font-semibold">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
              RECONNECTING {reconnectDelay ? `IN ${(reconnectDelay / 1000).toFixed(0)}s` : ''}...
            </span>
          </div>
        );
      case 'connecting':
        return (
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-xs text-slate-700">
            <span className="h-2 w-2 rounded-full bg-slate-500 animate-pulse"></span>
            <span className="font-mono font-medium">CONNECTING WS...</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-red-50 border border-red-300 text-xs text-red-700">
            <span className="h-2 w-2 rounded-full bg-red-600"></span>
            <span className="font-semibold flex items-center gap-1 font-mono">
              <WifiOff className="h-3.5 w-3.5" /> OFFLINE
            </span>
          </div>
        );
    }
  };

  const renderSystemStatusBadge = () => {
    switch (systemStatus) {
      case 'CRITICAL':
        return (
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-red-100 border border-red-300 text-xs font-mono font-bold text-red-700 shadow-sm">
            <AlertOctagon className="h-3.5 w-3.5 text-red-600 animate-pulse" />
            <span>SYSTEM: CRITICAL</span>
          </div>
        );
      case 'DEGRADED':
        return (
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-amber-100 border border-amber-300 text-xs font-mono font-bold text-amber-800">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
            <span>SYSTEM: DEGRADED</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-emerald-50 border border-emerald-300 text-xs font-mono font-bold text-emerald-700">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
            <span>SYSTEM: OPERATIONAL</span>
          </div>
        );
    }
  };

  return (
    <header className="border-b border-red-200 bg-white/95 backdrop-blur-md sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo & Title */}
        <div
          onClick={onNavigateHome}
          className={`flex items-center space-x-3 ${onNavigateHome ? 'cursor-pointer hover:opacity-90 transition-opacity' : ''}`}
        >
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-red-600 via-rose-500 to-red-500 flex items-center justify-center shadow-md shadow-red-500/20">
            <Shield className="h-6 w-6 text-white stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold tracking-tight text-slate-900">AegisOps</span>
              <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-red-50 text-red-600 border border-red-200 font-semibold">
                v{health?.version || '0.1.0'}
              </span>
            </div>
            <p className="text-xs text-slate-500">Autonomous AI Operations Center</p>
          </div>
        </div>

        {/* System Status Indicators & Controls */}
        <div className="flex items-center space-x-3 sm:space-x-4">
          {/* Section 1: System Status */}
          {renderSystemStatusBadge()}

          {/* Section 1: WebSocket Connection Status */}
          {renderConnectionBadge()}

          {/* AI Engine Provider Badge */}
          <div className="hidden lg:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs shadow-sm">
            <Activity className="h-3.5 w-3.5 text-red-500" />
            <span className="text-slate-500">AI:</span>
            <span className="text-red-600 font-bold uppercase">{health?.ai_engine?.provider || 'MOCK'}</span>
          </div>

          {/* Manual Refresh Sync Button */}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2 rounded-lg bg-slate-50 hover:bg-red-50 border border-slate-200 hover:border-red-200 text-slate-600 hover:text-red-600 transition shadow-sm disabled:opacity-50"
            title="Sync with Backend"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-red-600' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
