import React, { useState } from 'react';
import { useStationTelemetry } from '../hooks/useStationTelemetry';
import { DigitalTwinScene } from '../digital-twin/DigitalTwinScene';
import { TwinLegend } from '../digital-twin/TwinLegend';
import { SensorDetailsPanel } from '../digital-twin/SensorDetailsPanel';
import { DemoMode } from '../components/DemoMode';
import { StationSelector } from '../components/StationSelector';

export const DigitalTwin = () => {
  const {
    config,
    sensors,
    updateSensor,
    clearSensorOverrides,
    setScenario,
    activeStation,
    setActiveStation
  } = useStationTelemetry();

  const [selectedSensorId, setSelectedSensorId] = useState(null);
  const [showSensors, setShowSensors] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [showHeatmap, setShowHeatmap] = useState(true); // Default to ON for quick heatmap inspection
  const [resetTrigger, setResetTrigger] = useState(0);
  const [activeTestNum, setActiveTestNum] = useState(null);

  // Dynamically resolve selected sensor to react to telemetry updates & scenario changes
  const selectedSensor = React.useMemo(() => {
    if (!selectedSensorId) return null;
    return sensors.find((s) => s.id === selectedSensorId) || null;
  }, [selectedSensorId, sensors]);

  const stationTitle = config.displayName || `${config.stationId || 'MAITRI'} Research Station`;
  const stationCode = config.shortCode || config.id || 'MTR';

  const handleResetView = () => {
    setResetTrigger((prev) => prev + 1);
  };

  // Dedicated test sequence runner (TEST 1 - TEST 7 per specification)
  const handleRunTest = (testNum) => {
    setActiveTestNum(testNum);
    setShowHeatmap(true);

    // Pick first sensor in active station for consistent demonstration
    const targetSensor = sensors[0];

    switch (testNum) {
      case 1: // TEST 1: All sensors NORMAL -> station mostly clean, very subtle/no heatmap
        clearSensorOverrides();
        setScenario('NORMAL');
        setSelectedSensorId(null);
        break;

      case 2: // TEST 2: One sensor WARNING -> small/medium amber spatial region
        clearSensorOverrides();
        setScenario('NORMAL');
        setSelectedSensorId(null);
        if (targetSensor) {
          updateSensor(targetSensor.id, {
            status: 'WARNING',
            anomaly_score: 0.58,
            anomaly_status: 'WARNING'
          });
        }
        break;

      case 3: // TEST 3: Same sensor becomes CRITICAL -> stronger red region, larger radius, higher intensity
        if (targetSensor) {
          updateSensor(targetSensor.id, {
            status: 'CRITICAL',
            anomaly_score: 0.94,
            anomaly_status: 'CRITICAL'
          });
        }
        setSelectedSensorId(null);
        break;

      case 4: // TEST 4: Sensor becomes OFFLINE -> alarm heatmap disappears, sensor marker becomes gray
        if (targetSensor) {
          updateSensor(targetSensor.id, {
            status: 'OFFLINE',
            quality: 'LOST',
            anomaly_score: null,
            anomaly_status: 'OFFLINE'
          });
        }
        setSelectedSensorId(null);
        break;

      case 5: // TEST 5: Sensor returns to NORMAL -> heatmap fades away smoothly
        if (targetSensor) {
          updateSensor(targetSensor.id, {
            status: 'NORMAL',
            quality: 'GOOD',
            anomaly_score: 0.02,
            anomaly_status: 'NORMAL'
          });
        }
        setSelectedSensorId(null);
        break;

      case 6: // TEST 6: Click the sensor -> sensor detail panel opens, highlights sensor & heatmap contribution
        if (targetSensor) {
          updateSensor(targetSensor.id, {
            status: 'CRITICAL',
            anomaly_score: 0.92,
            anomaly_status: 'CRITICAL'
          });
          setSelectedSensorId(targetSensor.id);
        }
        break;

      case 7: // TEST 7: Switch MAITRI <-> BHARATI -> all heatmaps reposition correctly
        setActiveStation(activeStation === 'MAITRI' ? 'BHARATI' : 'MAITRI');
        setSelectedSensorId(null);
        break;

      default:
        break;
    }
  };

  return (
    <main className="main-viewport digital-twin-page-container">
      {/* Top Header */}
      <section className="twin-header-bar" aria-label="Digital Twin Header">
        <div className="twin-title-group">
          <h1>DIGITAL TWIN</h1>
          <p className="twin-subtitle">
            Antarctic station 3D spatial monitoring & dynamic data-driven heatmaps
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <StationSelector />
          <div className="sensors-station-stamp">
            <span className="station-badge-clean">
              {stationTitle.toUpperCase()} / {stationCode}
            </span>
            <span className="simulation-data-tag">
              SPATIAL HEATMAP • DATA-DRIVEN
            </span>
          </div>
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
              HEATMAP MODE: {showHeatmap ? 'ON' : 'OFF'}
            </button>

            {showHeatmap && (
              <span className="twin-inspection-badge" title="Roof transparency active for internal spatial condition inspection">
                INSPECTION MODE
              </span>
            )}

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

          {/* Quick Verification Toolbar (Tests 1-7) */}
          <div
            style={{
              position: 'absolute',
              top: '3.4rem',
              left: '1rem',
              zIndex: 15,
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              background: 'rgba(255, 255, 255, 0.94)',
              border: '1px solid var(--polaris-border)',
              borderRadius: 'var(--radius-xs)',
              padding: '0.35rem 0.6rem',
              backdropFilter: 'blur(8px)',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
            }}
          >
            <span style={{ fontSize: '0.625rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--polaris-text-muted)', marginRight: '0.25rem' }}>
              VERIFY SEQUENCE:
            </span>
            {[
              { id: 1, label: 'T1: NORMAL' },
              { id: 2, label: 'T2: WARNING' },
              { id: 3, label: 'T3: CRITICAL' },
              { id: 4, label: 'T4: OFFLINE' },
              { id: 5, label: 'T5: RECOVERY' },
              { id: 6, label: 'T6: SELECT' },
              { id: 7, label: 'T7: SWITCH' }
            ].map((t) => (
              <button
                key={t.id}
                type="button"
                className={`twin-tool-btn ${activeTestNum === t.id ? 'active' : ''}`}
                style={{ fontSize: '0.625rem', padding: '0.2rem 0.45rem' }}
                onClick={() => handleRunTest(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* 3D Scene */}
          <DigitalTwinScene
            station={config}
            sensors={sensors}
            selectedSensor={selectedSensor}
            onSelectSensor={(sensor) => setSelectedSensorId(sensor ? sensor.id : null)}
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
            onClose={() => setSelectedSensorId(null)}
          />
        )}
      </section>

      {/* Integrated Simulation Control (Demo Mode) */}
      <section style={{ marginTop: '0.75rem' }}>
        <DemoMode />
      </section>
    </main>
  );
};

export default DigitalTwin;
