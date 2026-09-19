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
import { isSensorMatchingMetric, normalizeSensorValue } from '../digital-twin/SpatialHeatmap';
import { ForecastController } from '../digital-twin/ForecastController';
import { calculateStationForecast } from '../services/forecastService';
import { AskTheTwinHUD } from '../digital-twin/AskTheTwinHUD';

// Mode definitions
const MODES = [
  { id: 'NORMAL',   label: 'NORMAL',   desc: 'Full station view — realistic appearance' },
  { id: 'XRAY',     label: 'X-RAY',    desc: 'Transparent shells — internal infrastructure visible' },
  { id: 'SYSTEM',   label: 'SYSTEM',   desc: 'Energy flow relationships and infrastructure dependencies' },
  { id: 'HEATMAP',  label: 'HEAT MAP', desc: 'Spatial telemetry intensity and sensor distribution field' },
  { id: 'FORECAST', label: 'FORECAST', desc: 'Operational resource forward projection (7 / 30 / 90 days)' },
  { id: 'REPLAY',   label: 'REPLAY',   desc: 'Incident playback timeline — backend data required' }
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

  const [twinMode, setTwinMode]                             = useState('NORMAL');
  const [heatmapMetric, setHeatmapMetric]                   = useState('TEMPERATURE');
  const [forecastHorizon, setForecastHorizon]               = useState(30);
  const [forecastDayOffset, setForecastDayOffset]           = useState(0);
  const [selectedSensorId, setSelectedSensorId]             = useState(null);
  const [selectedAsset, setSelectedAsset]                   = useState(null);
  const [showSensors, setShowSensors]                       = useState(true);
  const [showLabels, setShowLabels]                         = useState(true);
  const [resetTrigger, setResetTrigger]                     = useState(0);
  const [focusZone, setFocusZone]                           = useState(null);
  const [activeTestNum, setActiveTestNum]                   = useState(null);
  const [selectedIncidentNodeId, setSelectedIncidentNodeId] = useState(null);
  const [incidentBannerDismissed, setIncidentBannerDismissed] = useState(false);

  // ── Forecast Calculation ────────────────────────────────────────────────
  const forecastResult = React.useMemo(() => {
    if (twinMode !== 'FORECAST') return null;
    return calculateStationForecast({
      stationId: activeStation,
      horizonDays: forecastHorizon,
      dayOffset: forecastDayOffset,
      telemetry,
      sensors
    });
  }, [twinMode, activeStation, forecastHorizon, forecastDayOffset, telemetry, sensors]);

  // Project telemetry and sensors when in FORECAST mode
  const effectiveTelemetry = React.useMemo(() => {
    if (twinMode === 'FORECAST' && forecastResult && !forecastResult.isInsufficient) {
      return forecastResult.projectedTelemetry;
    }
    return telemetry;
  }, [twinMode, forecastResult, telemetry]);

  const effectiveSensors = React.useMemo(() => {
    if (twinMode === 'FORECAST' && forecastResult && !forecastResult.isInsufficient) {
      return forecastResult.projectedSensors;
    }
    return sensors;
  }, [twinMode, forecastResult, sensors]);

  // Dynamic metric options strictly computed from existing station sensors
  const availableHeatmapMetrics = React.useMemo(() => {
    const candidateMetrics = [
      { id: 'TEMPERATURE', label: 'TEMPERATURE' },
      { id: 'WIND',        label: 'WIND' },
      { id: 'POWER',       label: 'POWER' },
      { id: 'STRUCTURAL',  label: 'STRUCTURAL' },
      { id: 'FUEL',        label: 'FUEL' },
      { id: 'ALL',         label: 'ALL METRICS' }
    ];
    return candidateMetrics.filter(m => {
      if (m.id === 'ALL') return sensors.length > 0;
      return sensors.some(s => isSensorMatchingMetric(s, m.id));
    });
  }, [sensors]);

  // Keep heatmapMetric valid when station changes
  useEffect(() => {
    if (availableHeatmapMetrics.length > 0 && !availableHeatmapMetrics.some(m => m.id === heatmapMetric)) {
      setHeatmapMetric(availableHeatmapMetrics[0].id);
    }
  }, [availableHeatmapMetrics, heatmapMetric]);

  // Check if current metric has valid active telemetry
  const hasTelemetryForMetric = React.useMemo(() => {
    return sensors.some(s => isSensorMatchingMetric(s, heatmapMetric) && normalizeSensorValue(s) !== null);
  }, [sensors, heatmapMetric]);

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
    return effectiveSensors.find((s) => s.id === selectedSensorId) || null;
  }, [selectedSensorId, effectiveSensors]);

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
          {twinMode === 'FORECAST' ? (
            <span
              className="simulation-data-tag"
              style={{
                background: forecastDayOffset === 0 ? 'rgba(63, 110, 74, 0.12)' : 'rgba(182, 90, 31, 0.14)',
                color: forecastDayOffset === 0 ? 'var(--polaris-green)' : 'var(--polaris-copper)',
                borderColor: forecastDayOffset === 0 ? 'rgba(63, 110, 74, 0.35)' : 'rgba(182, 90, 31, 0.4)'
              }}
            >
              {forecastDayOffset === 0 ? '● LIVE BASELINE (T+0.0d)' : `🔮 FORECAST: +${forecastDayOffset.toFixed(1)}d (${forecastHorizon}d)`}
            </span>
          ) : (
            <span className="simulation-data-tag">
              {activeScenario && activeScenario !== 'NORMAL' ? `SCENARIO: ${activeScenario}` : 'LIVE TELEMETRY'}
            </span>
          )}
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

      {/* ── Forecast Horizon Strip (Visible in FORECAST mode) ── */}
      {twinMode === 'FORECAST' ? (
        <div className="twin-component-strip" role="toolbar" aria-label="Select Forecast Horizon">
          <span className="twin-component-label">FORECAST HORIZON:</span>
          {[7, 30, 90].map(h => (
            <button
              key={h}
              type="button"
              className={`twin-comp-chip ${forecastHorizon === h ? 'active' : ''}`}
              onClick={() => {
                setForecastHorizon(h);
                if (forecastDayOffset > h) setForecastDayOffset(h);
              }}
            >
              <span className="twin-comp-dot" />
              {h} DAYS
            </button>
          ))}
          <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: '0.62rem', color: forecastDayOffset === 0 ? 'var(--polaris-green)' : 'var(--polaris-copper)', fontWeight: 600 }}>
            {forecastDayOffset === 0
              ? '● LIVE STATE (T+0.0d)'
              : `FORECAST STATE (+${forecastDayOffset.toFixed(1)}d of ${forecastHorizon}d)`}
          </span>
        </div>
      ) : twinMode === 'HEATMAP' ? (
        <div className="twin-component-strip" role="toolbar" aria-label="Select Heat Map Metric">
          <span className="twin-component-label">HEAT MAP METRIC:</span>
          {availableHeatmapMetrics.map(metric => (
            <button
              key={metric.id}
              type="button"
              className={`twin-comp-chip ${heatmapMetric === metric.id ? 'active' : ''}`}
              onClick={() => setHeatmapMetric(metric.id)}
            >
              <span className="twin-comp-dot" />
              {metric.label}
            </button>
          ))}
        </div>
      ) : (
        /* ── Infrastructure Component Quick Selector Strip (Normal / X-Ray / System modes) ── */
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
      )}

      {/* ── Main 3D Viewport Card ── */}
      <section className="twin-viewport-card" aria-label="3D Spatial Model Viewport">
        <div className="twin-canvas-wrapper">

          {/* Top-Left: Station Status HUD (Matching Authentic Reference Design) */}
          <StationStatusHUD
            telemetry={effectiveTelemetry}
            sensors={effectiveSensors}
            config={config}
          />

          {/* Top-Left Mission-Control Command Bar: ASK THE TWIN */}
          {noPanelOpen && (
            <AskTheTwinHUD
              stationCode={stationCode}
              stationTitle={stationTitle}
              telemetry={effectiveTelemetry}
              sensors={effectiveSensors}
              readiness={config?.readiness}
            />
          )}

          {/* Top-Right & Bottom-Right HUDs (Visible when inspect panel is not open) */}
          {noPanelOpen && (
            <>
              <EnvironmentalFeedHUD telemetry={effectiveTelemetry} />
              <RealtimeEventLogHUD telemetry={effectiveTelemetry} alerts={config?.alerts} />
            </>
          )}

          {/* ── INCIDENT BANNER — top-center when incident active ── */}
          {incidentGraph.isActive && !incidentBannerDismissed && (
            <IncidentBanner
              incidentGraph={incidentGraph}
              onDismiss={() => setIncidentBannerDismissed(true)}
            />
          )}

          {/* FORECAST mode state badge */}
          {twinMode === 'FORECAST' && (
            <div
              className="twin-inspection-chip"
              style={{
                background: forecastResult?.isInsufficient
                  ? 'rgba(217, 130, 26, 0.12)'
                  : forecastDayOffset === 0
                  ? 'rgba(63, 110, 74, 0.12)'
                  : 'rgba(182, 90, 31, 0.14)',
                color: forecastResult?.isInsufficient
                  ? 'var(--polaris-amber)'
                  : forecastDayOffset === 0
                  ? 'var(--polaris-green)'
                  : 'var(--polaris-copper)',
                borderColor: forecastResult?.isInsufficient
                  ? 'rgba(217, 130, 26, 0.4)'
                  : forecastDayOffset === 0
                  ? 'rgba(63, 110, 74, 0.35)'
                  : 'rgba(182, 90, 31, 0.4)'
              }}
            >
              {forecastResult?.isInsufficient
                ? '⚠️ DATA INSUFFICIENT'
                : forecastDayOffset === 0
                ? 'LIVE STATE BASELINE — T+0.0 DAYS'
                : `FORECAST STATE — PROJECTED T+${forecastDayOffset.toFixed(1)} DAYS (${forecastHorizon}D HORIZON)`}
            </div>
          )}

          {/* Insufficient Data Overlay in Center of Viewport */}
          {twinMode === 'FORECAST' && forecastResult?.isInsufficient && (
            <div
              style={{
                position: 'absolute',
                top: '46%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                background: 'rgba(25, 28, 32, 0.94)',
                color: '#f8f6f0',
                padding: '14px 26px',
                borderRadius: '6px',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '13px',
                fontWeight: 700,
                letterSpacing: '0.08em',
                border: '1px solid rgba(217, 130, 26, 0.45)',
                boxShadow: '0 8px 30px rgba(0,0,0,0.4)',
                zIndex: 35,
                pointerEvents: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <span style={{ color: '#d9821a' }}>⚠️</span>
              DATA INSUFFICIENT FOR FORWARD PROJECTION
            </div>
          )}

          {/* Heatmap inspection badge (HEATMAP mode only) */}
          {twinMode === 'HEATMAP' && (
            <div className="twin-inspection-chip" style={{ background: 'rgba(43, 92, 143, 0.12)', color: '#2b5c8f', borderColor: 'rgba(43, 92, 143, 0.35)' }}>
              HEAT MAP MODE — {heatmapMetric} SPATIAL INTENSITY FIELD
            </div>
          )}

          {/* Missing Telemetry Overlay Banner */}
          {twinMode === 'HEATMAP' && !hasTelemetryForMetric && (
            <div
              style={{
                position: 'absolute',
                top: '46%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                background: 'rgba(25, 28, 32, 0.94)',
                color: '#f8f6f0',
                padding: '14px 26px',
                borderRadius: '6px',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '13px',
                fontWeight: 700,
                letterSpacing: '0.08em',
                border: '1px solid rgba(217, 130, 26, 0.45)',
                boxShadow: '0 8px 30px rgba(0,0,0,0.4)',
                zIndex: 35,
                pointerEvents: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <span style={{ color: '#d9821a' }}>⚠️</span>
              NO TELEMETRY AVAILABLE FOR {heatmapMetric}
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
            sensors={effectiveSensors}
            telemetry={effectiveTelemetry}
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
            heatmapMetric={heatmapMetric}
            incidentGraph={incidentGraph}
            onIncidentNodeClick={handleIncidentNodeClick}
            selectedIncidentNodeId={selectedIncidentNodeId}
          />

          {/* Legend */}
          {twinMode !== 'REPLAY' && (
            <TwinLegend
              sensors={effectiveSensors}
              isHeatmapActive={twinMode === 'HEATMAP'}
              isSystemActive={twinMode === 'SYSTEM'}
              telemetry={effectiveTelemetry}
              heatmapMetric={heatmapMetric}
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

      {/* FORECAST mode timeline dock */}
      {twinMode === 'FORECAST' && (
        <section style={{ marginTop: '0.75rem' }}>
          <ForecastController
            stationCode={stationCode}
            horizonDays={forecastHorizon}
            onHorizonChange={setForecastHorizon}
            dayOffset={forecastDayOffset}
            onDayOffsetChange={setForecastDayOffset}
            forecastResult={forecastResult}
          />
        </section>
      )}

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

