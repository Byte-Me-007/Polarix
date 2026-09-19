import React, { useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { useStationTelemetry } from '../hooks/useStationTelemetry';
import { DigitalTwinScene } from '../digital-twin/DigitalTwinScene';
import { TwinLegend } from '../digital-twin/TwinLegend';
import { SensorDetailsPanel } from '../digital-twin/SensorDetailsPanel';
import { AssetInspectPanel } from '../digital-twin/AssetInspectPanel';
import { ReplayController } from '../digital-twin/ReplayController';
import { StationStatusHUD, EnvironmentalFeedHUD, RealtimeEventLogHUD } from '../digital-twin/StationHUDOverlays';
import { IncidentBanner } from '../digital-twin/IncidentBanner';
import { IncidentSummaryPanel } from '../digital-twin/IncidentSummaryPanel';
import { useIncidentGraph } from '../digital-twin/useIncidentGraph';
import { DemoMode } from '../components/DemoMode';
import { StationSelector } from '../components/StationSelector';
import { useStation } from '../context/StationContext';

// Mode definitions
const MODES = [
  { id: 'NORMAL',  label: 'NORMAL',  desc: 'Full station view — realistic appearance' },
  { id: 'XRAY',    label: 'X-RAY',   desc: 'Transparent shells — internal infrastructure visible' },
  { id: 'SYSTEM',  label: 'SYSTEM',  desc: 'Energy flow relationships and infrastructure dependencies' },
  { id: 'HEATMAP', label: 'HEATMAP', desc: 'Spatial sensor condition anomaly intensity overlay' },
  { id: 'REPLAY',  label: 'REPLAY',  desc: 'Incident playback timeline — backend data required' }
];

export const DigitalTwin = () => {
  const location = useLocation();
  const {
    config,
    sensors,
    updateSensor,
    clearSensorOverrides,
    setScenario,
    activeStation,
    setActiveStation,
    activeScenario
  } = useStationTelemetry();

  const { telemetry } = useStation();

  // ── Derived incident graph (state-based, no fake data) ───────────────────
  const incidentGraph = useIncidentGraph();

  const [twinMode, setTwinMode]                     = useState('NORMAL');
  const [selectedSensorId, setSelectedSensorId]     = useState(null);
  const [selectedAsset, setSelectedAsset]           = useState(null);
  const [showSensors, setShowSensors]               = useState(true);
  const [showLabels, setShowLabels]                 = useState(true);
  const [resetTrigger, setResetTrigger]             = useState(0);
  const [focusZone, setFocusZone]                   = useState(null);
  const [activeTestNum, setActiveTestNum]           = useState(null);
  const [selectedIncidentNodeId, setSelectedIncidentNodeId] = useState(null);
  const [incidentBannerDismissed, setIncidentBannerDismissed] = useState(false);

  // Clear all spatial selection state when station changes
  // (sensor/asset positions are station-specific; stale selection would be meaningless)
  useEffect(() => {
    setSelectedIncidentNodeId(null);
    setIncidentBannerDismissed(false);
    setSelectedSensorId(null);
    setSelectedAsset(null);
    setFocusZone(null);
    // Trigger camera reset so view jumps to correct station overview
    setResetTrigger(prev => prev + 1);
  }, [activeStation]);

  // Clear incident focus when scenario returns to NORMAL/RECOVERY
  useEffect(() => {
    if (!incidentGraph.isActive) {
      setSelectedIncidentNodeId(null);
      setIncidentBannerDismissed(false);
    }
  }, [incidentGraph.isActive]);

  // ── Cross-module navigation state handling ───────────────────────────────
  useEffect(() => {
    const state = location.state;
    if (!state) return;

    // From Alerts: { locateSensorId, highlightZone, twinMode }
    if (state.locateSensorId) {
      setSelectedSensorId(state.locateSensorId);
      setShowSensors(true);
    }
    // From Alerts / Energy / Logistics: { focusZone, twinMode }
    if (state.focusZone) {
      setFocusZone(state.focusZone);
    }
    // Incoming mode override
    if (state.twinMode && MODES.find(m => m.id === state.twinMode)) {
      setTwinMode(state.twinMode);
    }
  }, [location.state]);

  // Clear focusZone after a delay so it doesn't lock camera
  useEffect(() => {
    if (!focusZone) return;
    const timer = setTimeout(() => setFocusZone(null), 3500);
    return () => clearTimeout(timer);
  }, [focusZone]);

  // Dynamically resolve selected sensor
  const selectedSensor = React.useMemo(() => {
    if (!selectedSensorId) return null;
    return sensors.find((s) => s.id === selectedSensorId) || null;
  }, [selectedSensorId, sensors]);

  const stationTitle = config.displayName || `${config.stationId || 'MAITRI'} Research Station`;
  const stationCode  = config.shortCode || config.id || 'MTR';

  const handleResetView = () => {
    setResetTrigger(prev => prev + 1);
    setFocusZone(null);
    setSelectedIncidentNodeId(null);
  };

  const handleModeChange = (modeId) => {
    setTwinMode(modeId);
    // Clear sensor + asset selection when switching modes
    if (modeId !== 'HEATMAP') {
      // preserve sensor selection in heatmap
    }
  };

  const handleSelectAsset = useCallback((asset) => {
    setSelectedAsset(asset);
    setSelectedSensorId(null); // close sensor panel if open
    // Switch to X-RAY so user can see inside
    setTwinMode(prev => prev === 'NORMAL' ? 'XRAY' : prev);
    if (asset?.zone) {
      setFocusZone(asset.zone);
    }
  }, []);

  const handleCloseAssetPanel = useCallback(() => {
    setSelectedAsset(null);
  }, []);

  const handleSelectSensor = useCallback((sensor) => {
    setSelectedSensorId(sensor ? sensor.id : null);
    setSelectedAsset(null); // close asset panel if open
  }, []);

  const handleCloseSensorPanel = useCallback(() => {
    setSelectedSensorId(null);
  }, []);

  // ── Incident node click handler ──────────────────────────────────────────
  // Clicking an incident node focuses the camera on the zone,
  // then opens the asset inspect panel for the associated asset.
  const handleIncidentNodeClick = useCallback((node) => {
    setSelectedIncidentNodeId(node.id);
    setSelectedSensorId(null);

    if (node.asset) {
      // Open asset inspection — reuse existing panel
      setSelectedAsset(node.asset);
      setTwinMode(prev => (prev === 'NORMAL' ? 'XRAY' : prev));
    }
    if (node.zoneCode) {
      setFocusZone(node.zoneCode);
    }
  }, []);

  // ── Incident sensor click handler ────────────────────────────────────────
  // Clicking a sensor ID in the IncidentSummaryPanel opens SensorDetailsPanel
  const handleIncidentSensorClick = useCallback((sensorId) => {
    if (!sensorId) return;
    setSelectedSensorId(sensorId);
    setSelectedAsset(null);
    setShowSensors(true);
    // Find the sensor to derive its zone for camera focus
    const sensor = sensors.find(s => s.id === sensorId);
    if (sensor?.zone) setFocusZone(sensor.zone);
  }, [sensors]);

  // Scenario-based test sequence (T1–T7, preserved from original)
  const handleRunTest = (testNum) => {
    setActiveTestNum(testNum);
    if (testNum !== 1) setTwinMode(prev => prev); // keep mode

    const targetSensor = sensors[0];

    switch (testNum) {
      case 1:
        clearSensorOverrides();
        setScenario('NORMAL');
        setSelectedSensorId(null);
        break;
      case 2:
        clearSensorOverrides();
        setScenario('NORMAL');
        setSelectedSensorId(null);
        if (targetSensor) {
          updateSensor(targetSensor.id, { status: 'WARNING', anomaly_score: 0.58, anomaly_status: 'WARNING' });
        }
        break;
      case 3:
        if (targetSensor) {
          updateSensor(targetSensor.id, { status: 'CRITICAL', anomaly_score: 0.94, anomaly_status: 'CRITICAL' });
        }
        setSelectedSensorId(null);
        break;
      case 4:
        if (targetSensor) {
          updateSensor(targetSensor.id, { status: 'OFFLINE', quality: 'LOST', anomaly_score: null, anomaly_status: 'OFFLINE' });
        }
        setSelectedSensorId(null);
        break;
      case 5:
        if (targetSensor) {
          updateSensor(targetSensor.id, { status: 'NORMAL', quality: 'GOOD', anomaly_score: 0.02, anomaly_status: 'NORMAL' });
        }
        setSelectedSensorId(null);
        break;
      case 6:
        if (targetSensor) {
          setSelectedSensorId(targetSensor.id);
        }
        break;
      case 7:
        setActiveStation(prev => prev === 'MAITRI' ? 'BHARATI' : 'MAITRI');
        break;
      default:
        break;
    }
  };

  const currentModeDesc = MODES.find(m => m.id === twinMode)?.desc || '';

  // Whether both side panels are closed (controls whether HUDs are visible)
  const noPanelOpen = !selectedAsset && !selectedSensor;
  // Incident panel is compact when a sensor/asset panel is open
  const incidentPanelCompact = Boolean(selectedAsset || selectedSensor);

  return (
    <main className="main-viewport digital-twin-page">

      {/* ── Top Header Bar (Standard Polaris Layout) ── */}
      <section className="sensors-header-bar" aria-label="Digital Twin Overview">
        <div className="sensors-title-group">
          <h1>DIGITAL TWIN</h1>
          <p className="sensors-subtitle">
            {currentModeDesc || 'Operational 3D spatial twin and facility telemetry monitor'}
          </p>
        </div>

        <div className="sensors-station-stamp">
          <span className="station-badge-clean">
            {stationTitle.toUpperCase()} / {stationCode} • {config?.zones?.length || 6} MODULES • {sensors.length} SENSORS
          </span>
          <span className="simulation-data-tag">
            {activeScenario && activeScenario !== 'NORMAL' ? `SCENARIO: ${activeScenario}` : 'LIVE TELEMETRY'}
          </span>
        </div>
      </section>

      {/* ── Mode Switcher & Viewport Toolbar ── */}
      <div className="twin-mode-strip" role="toolbar" aria-label="Digital Twin Mode Controls">
        <div className="twin-mode-switcher">
          {MODES.map(mode => (
            <button
              key={mode.id}
              type="button"
              className={`twin-mode-btn ${twinMode === mode.id ? 'active' : ''}`}
              onClick={() => handleModeChange(mode.id)}
              title={mode.desc}
            >
              {mode.label}
              {mode.id === 'REPLAY' && (
                <span className="twin-mode-badge-dot" />
              )}
            </button>
          ))}
        </div>

        {/* Quick control strip on the right */}
        <div className="twin-quick-controls">
          <button
            type="button"
            className={`twin-tool-btn-sm ${showSensors ? 'active' : ''}`}
            onClick={() => setShowSensors(v => !v)}
            title="Toggle sensor markers"
          >
            {showSensors ? 'SENSORS: ON' : 'SENSORS: OFF'}
          </button>
          <button
            type="button"
            className={`twin-tool-btn-sm ${showLabels ? 'active' : ''}`}
            onClick={() => setShowLabels(v => !v)}
            title="Toggle zone labels"
          >
            {showLabels ? 'LABELS: ON' : 'LABELS: OFF'}
          </button>
          <button
            type="button"
            className="twin-tool-btn-sm"
            onClick={handleResetView}
            title="Reset camera to full station overview"
          >
            RESET VIEW
          </button>
        </div>
      </div>

      {/* ── Infrastructure Component Quick Selector Strip ── */}
      <div className="twin-component-strip" role="toolbar" aria-label="Select Infrastructure Component">
        <span className="twin-component-label">INFRASTRUCTURE ASSETS:</span>
        {[
          { id: 'ENERGY-BATT-01',    type: 'BATTERY',     label: 'BATTERY BANK A',  zone: 'ENERGY', status: 'RUNNING' },
          { id: 'ENERGY-BATT-02',    type: 'BATTERY',     label: 'BATTERY BANK B',  zone: 'ENERGY', status: 'RUNNING' },
          { id: 'ENERGY-INV-01',     type: 'INVERTER',    label: 'MICROGRID INV.',  zone: 'ENERGY', status: 'RUNNING' },
          { id: 'ENERGY-TRANS-01',   type: 'TRANSFORMER', label: 'HV TRANSFORMER',  zone: 'ENERGY', status: 'RUNNING' },
          { id: 'GENERATOR-GEN-01',  type: 'GENERATOR',   label: 'DIESEL GEN #1',   zone: 'GENERATOR', status: 'RUNNING' },
          { id: 'GENERATOR-GEN-02',  type: 'GENERATOR',   label: 'DIESEL GEN #2',   zone: 'GENERATOR', status: 'RUNNING' },
          { id: 'GENERATOR-FUEL-01', type: 'FUEL_TANK',   label: 'DAY TANK',        zone: 'GENERATOR', status: 'RUNNING' },
          { id: 'MAIN-HVAC-01',      type: 'HVAC',        label: 'HVAC UNIT A',     zone: 'MAIN', status: 'RUNNING' },
          { id: 'RESEARCH-RES-01',   type: 'RESEARCH',    label: 'MET ARRAY',       zone: 'RESEARCH', status: 'RUNNING' },
          { id: 'STORAGE-FREEZE-01', type: 'FREEZER',     label: 'CRYO FREEZER',    zone: 'STORAGE', status: 'RUNNING' },
        ].map(comp => (
          <button
            key={comp.id}
            type="button"
            className={`twin-comp-chip ${selectedAsset?.id === comp.id ? 'active' : ''}`}
            onClick={() => handleSelectAsset(comp)}
          >
            <span className="twin-comp-dot" />
            {comp.label}
          </button>
        ))}
      </div>

      {/* ── Main 3D Viewport Card ── */}
      <section className="twin-viewport-card" aria-label="3D Spatial Model Viewport">
        <div className="twin-canvas-wrapper">

          {/* Top-Left: Station Status HUD (Matching Authentic Reference Design) */}
          <StationStatusHUD
            telemetry={telemetry}
            sensors={sensors}
            config={config}
          />

          {/* Top-Right & Bottom-Right HUDs (Visible when inspect panel is not open) */}
          {noPanelOpen && (
            <>
              <EnvironmentalFeedHUD telemetry={telemetry} />
              <RealtimeEventLogHUD telemetry={telemetry} alerts={config?.alerts} />
            </>
          )}

          {/* ── INCIDENT BANNER — top-center when incident active ── */}
          {incidentGraph.isActive && !incidentBannerDismissed && (
            <IncidentBanner
              incidentGraph={incidentGraph}
              onDismiss={() => setIncidentBannerDismissed(true)}
            />
          )}

          {/* Heatmap inspection badge (HEATMAP mode only) */}
          {twinMode === 'HEATMAP' && (
            <div className="twin-inspection-chip">
              INSPECTION MODE — TRANSPARENT ROOF
            </div>
          )}

          {/* X-RAY mode badge */}
          {twinMode === 'XRAY' && (
            <div className="twin-inspection-chip" style={{ background: 'rgba(182,90,31,0.10)', color: '#b65a1f', borderColor: 'rgba(182,90,31,0.28)' }}>
              X-RAY MODE — INTERNAL INFRASTRUCTURE VISIBLE
            </div>
          )}

          {/* SYSTEM mode badge */}
          {twinMode === 'SYSTEM' && (
            <div className="twin-inspection-chip" style={{ background: 'rgba(79,111,82,0.10)', color: '#4f6f52', borderColor: 'rgba(79,111,82,0.28)' }}>
              SYSTEM MODE — ENERGY FLOW VISUALIZATION
            </div>
          )}

          {/* 3D Scene */}
          <DigitalTwinScene
            station={config}
            sensors={sensors}
            telemetry={telemetry}
            selectedSensor={selectedSensor}
            onSelectSensor={(sensor) => {
              setSelectedSensorId(sensor ? sensor.id : null);
              setSelectedAsset(null);
            }}
            showSensors={showSensors}
            showLabels={showLabels}
            showHeatmap={twinMode === 'HEATMAP'}
            resetTrigger={resetTrigger}
            twinMode={twinMode}
            focusZone={focusZone}
            onSelectAsset={handleSelectAsset}
            selectedAssetId={selectedAsset?.id}
            activeStation={activeStation}
            incidentGraph={incidentGraph}
            onIncidentNodeClick={handleIncidentNodeClick}
            selectedIncidentNodeId={selectedIncidentNodeId}
          />

          {/* Legend */}
          {twinMode !== 'REPLAY' && (
            <TwinLegend
              sensors={sensors}
              isHeatmapActive={twinMode === 'HEATMAP'}
              isSystemActive={twinMode === 'SYSTEM'}
              telemetry={telemetry}
            />
          )}

          {/* Camera nav hint */}
          <div className="twin-nav-hint">
            L-CLICK: ROTATE &nbsp;|&nbsp; R-CLICK: PAN &nbsp;|&nbsp; SCROLL: ZOOM
          </div>

          {/* ── INCIDENT SUMMARY PANEL — bottom-left when incident active ── */}
          <IncidentSummaryPanel
            incidentGraph={incidentGraph}
            onSelectNode={handleIncidentNodeClick}
            onSelectSensor={handleIncidentSensorClick}
            isCompact={incidentPanelCompact}
          />
        </div>

        {/* Sensor Detail Panel */}
        {selectedSensor && !selectedAsset && (
          <SensorDetailsPanel
            sensor={selectedSensor}
            onClose={() => setSelectedSensorId(null)}
          />
        )}

        {/* Asset Inspect Panel */}
        {selectedAsset && !selectedSensor && (
          <AssetInspectPanel
            asset={selectedAsset}
            onClose={handleCloseAssetPanel}
          />
        )}
      </section>

      {/* ── Operational Diagnostics & Verification Test Sequence (T1–T7) ── */}
      <section className="twin-diagnostics-section" aria-label="Operational Verification Suite">
        <div className="twin-diagnostics-header">
          <div className="twin-diagnostics-title">
            <span style={{ color: 'var(--polaris-copper)' }}>⚡</span>
            OPERATIONAL VERIFICATION &amp; TEST SEQUENCE (T1–T7)
          </div>
          <span style={{ fontSize: '0.6rem', color: 'var(--polaris-text-muted)', fontFamily: 'var(--font-mono)' }}>
            Targeted State &amp; Telemetry Validation
          </span>
        </div>
        <div className="twin-diagnostics-grid">
          {[
            { id: 1, label: 'T1: NORMAL', desc: 'Restore nominal state and clear overrides' },
            { id: 2, label: 'T2: WARNING', desc: 'Inject warning status and anomaly score 0.58' },
            { id: 3, label: 'T3: CRITICAL', desc: 'Inject critical status and anomaly score 0.94' },
            { id: 4, label: 'T4: OFFLINE', desc: 'Drop telemetry connection to offline' },
            { id: 5, label: 'T5: RECOVERY', desc: 'Execute recovery cycle to healthy baseline' },
            { id: 6, label: 'T6: SELECT SENSOR', desc: 'Target and select active sensor marker' },
            { id: 7, label: 'T7: SWITCH STATION', desc: 'Toggle between Maitri and Bharati stations' }
          ].map((t) => (
            <button
              key={t.id}
              type="button"
              className={`twin-diagnostics-btn ${activeTestNum === t.id ? 'active' : ''}`}
              onClick={() => handleRunTest(t.id)}
              title={t.desc}
            >
              <span>{t.label}</span>
            </button>
          ))}
        </div>
      </section>

      {/* REPLAY mode timeline dock */}
      {twinMode === 'REPLAY' && (
        <section style={{ marginTop: '0.75rem' }}>
          <ReplayController activeScenario={activeScenario} />
        </section>
      )}

      {/* Integrated Simulation Control (Demo Mode) */}
      <section style={{ marginTop: '0.75rem' }}>
        <DemoMode />
      </section>
    </main>
  );
};

export default DigitalTwin;

