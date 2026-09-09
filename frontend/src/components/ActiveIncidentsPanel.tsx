import React from 'react';
import { IncidentsTable } from './IncidentsTable';
import { Incident } from '../types';

export interface ActiveIncidentsPanelProps {
  incidents: Incident[];
  onResolve: (id: string) => Promise<void>;
  onSimulateDrill: () => Promise<void>;
  onSelectIncident?: (incident: Incident) => void;
  loading: boolean;
}

export const ActiveIncidentsPanel: React.FC<ActiveIncidentsPanelProps> = ({
  incidents,
  onResolve,
  onSimulateDrill,
  onSelectIncident,
  loading,
}) => {
  return (
    <IncidentsTable
      incidents={incidents}
      onSelectIncident={onSelectIncident || (() => {})}
      onResolve={onResolve}
      onSimulateDrill={onSimulateDrill}
      loading={loading}
    />
  );
};

