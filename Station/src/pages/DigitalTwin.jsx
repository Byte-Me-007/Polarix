import React, { useState } from 'react';
import { useStationTelemetry } from '../hooks/useStationTelemetry';
import { DigitalTwinScene } from '../digital-twin/DigitalTwinScene';
import { TwinLegend } from '../digital-twin/TwinLegend';
import { SensorDetailsPanel } from '../digital-twin/SensorDetailsPanel';

export const DigitalTwin = () => {
  const { config, sensors } = useStationTelemetry();

  const [selectedSensor, setSelectedSensor] = useState(null);
  const [showSensors, setShowSensors] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [resetTrigger, setResetTrigger] = useState(0);

  const stationTitle = config.displayName || `${config.stationId || 'MAITRI'} Research Station`;
  const stationCode = config.shortCode || config.id || 'MTR';

  const handleResetView = () => {
    setResetTrigger((prev) => prev + 1);
  };

  return (
    <main className="main-viewport digital-twin-page-container">
      {/* Top Header */}
      <section className="twin-header-bar" aria-label="Digital Twin Header">
        <div className="twin-title-group">
          <h1>DIGITAL TWIN</h1>
          <p className="twin-subtitle">
            Antarctic station 3D spatial monitoring and telemetry mapping
          </p>
        </div>

        <div className="sensors-station-stamp">
          <span className="station-badge-clean">
            {stationTitle.toUpperCase()} / {stationCode}
          </span>
          <span className="simulation-data-tag">
            SPATIAL MONITORING • DEMO TELEMETRY
          </span>
        </div>
      </section>

      {/* Main 3D Viewport Card */}
      <section className="twin-viewport-card" aria-label="3D Spatial Model Viewport">
        <div className="twin-canvas-wrapper">
          {/* View Controls Overlay */}
          <div className="twin-toolbar-overlay" role="toolbar" aria-label="3D Viewport Controls">
            <button
              type="button"
              className="twin-tool-btn"
              onClick={handleResetView}
              title="Reset camera angle to default perspective"
            >
              RESET VIEW
            </button>

            <button
              type="button"
              className={`twin-tool-btn ${showHeatmap ? 'active' : ''}`}
              onClick={() => setShowHeatmap(!showHeatmap)}
              title="Toggle 3D spatial sensor condition heatmap"
            >
              HEATMAP: {showHeatmap ? 'ON' : 'OFF'}
            </button>

            <button
              type="button"
              className={`twin-tool-btn ${showSensors ? 'active' : ''}`}
              onClick={() => setShowSensors(!showSensors)}
              title="Toggle 3D sensor markers visibility"
            >
              {showSensors ? 'HIDE SENSORS' : 'SHOW SENSORS'}
            </button>

            <button
              type="button"
              className={`twin-tool-btn ${showLabels ? 'active' : ''}`}
              onClick={() => setShowLabels(!showLabels)}
              title="Toggle zone name labels"
            >
              {showLabels ? 'HIDE LABELS' : 'SHOW LABELS'}
            </button>
          </div>

          {/* 3D Scene */}
          <DigitalTwinScene
            station={config}
            sensors={sensors}
            selectedSensor={selectedSensor}
            onSelectSensor={setSelectedSensor}
            showSensors={showSensors}
            showLabels={showLabels}
            showHeatmap={showHeatmap}
            resetTrigger={resetTrigger}
          />

          {/* Status Color Legend with Dynamic Counts & Heatmap Mode */}
          <TwinLegend sensors={sensors} isHeatmapActive={showHeatmap} />

          {/* Camera Navigation Tip */}
          <div className="twin-nav-hint">
            L-CLICK: ROTATE &nbsp;|&nbsp; R-CLICK: PAN &nbsp;|&nbsp; SCROLL: ZOOM
          </div>
        </div>

        {/* Selected Sensor Detail Drawer (Overlaid on Viewport) */}
        {selectedSensor && (
          <SensorDetailsPanel
            sensor={selectedSensor}
            onClose={() => setSelectedSensor(null)}
          />
        )}
      </section>
    </main>
  );
};

export default DigitalTwin;
