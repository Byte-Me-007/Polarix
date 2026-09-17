import React from 'react';
import { useStationTelemetry } from '../hooks/useStationTelemetry';
import { STATIONS } from '../data/stationData';

export const StationSelector = () => {
  const { activeStation, setActiveStation } = useStationTelemetry();

  return (
    <div className="instrument-station-selector" role="group" aria-label="Select Antarctic Station">
      {Object.values(STATIONS).map((st) => {
        const isActive = activeStation === st.stationId;
        return (
          <button
            key={st.stationId}
            type="button"
            className={`station-tab-btn ${isActive ? 'active' : ''}`}
            onClick={() => setActiveStation(st.stationId)}
          >
            <span>{st.stationId}</span>
            <span className="station-tab-tag">{st.shortCode}</span>
          </button>
        );
      })}
    </div>
  );
};

export default StationSelector;
