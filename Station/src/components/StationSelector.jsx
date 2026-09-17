import React from 'react';
import { useStationTelemetry } from '../hooks/useStationTelemetry';

export const StationSelector = () => {
  const { activeStation, setActiveStation } = useStationTelemetry();

  return (
    <div className="instrument-station-selector" role="group" aria-label="Select Antarctic Station">
      <button
        type="button"
        className={`station-tab-btn ${activeStation === 'MAITRI' ? 'active' : ''}`}
        onClick={() => setActiveStation('MAITRI')}
      >
        <span>MAITRI</span>
        <span className="station-tab-tag">MTR</span>
      </button>

      <button
        type="button"
        className={`station-tab-btn ${activeStation === 'BHARATI' ? 'active' : ''}`}
        onClick={() => setActiveStation('BHARATI')}
      >
        <span>BHARATI</span>
        <span className="station-tab-tag">BHR</span>
      </button>
    </div>
  );
};

export default StationSelector;
