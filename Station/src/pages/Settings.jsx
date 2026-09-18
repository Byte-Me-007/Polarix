import React, { useState, useEffect } from 'react';
import { useStationTelemetry } from '../hooks/useStationTelemetry';
import { DEMO_SCENARIOS } from '../data/stationData';

/**
 * Settings (Mission Control Configuration Console)
 * 
 * Professional station configuration and operational threshold management.
 * Strictly uses shared application state (StationContext, telemetry, thresholds, demo scenario).
 * Adheres directly to the POLARIS scientific light theme.
 */
export const Settings = () => {
  const {
    activeStation,
    setActiveStation,
    config,
    telemetry,
    thresholds,
    updateThreshold,
    updateThresholds,
    resetThresholds,
    resetStationState,
    scenario,
    setScenario,
    demoModeEnabled,
    setDemoModeEnabled,
    lastUpdated
  } = useStationTelemetry();

  // Local draft threshold state for editing
  const [draftThresholds, setDraftThresholds] = useState({ ...thresholds });
  const [saveFeedback, setSaveFeedback] = useState(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  // Keep draft in sync if external reset occurs
  useEffect(() => {
    setDraftThresholds({ ...thresholds });
  }, [thresholds]);

  // Live second tick for clock readouts
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleInputChange = (field, val) => {
    const num = parseFloat(val);
    setDraftThresholds(prev => ({
      ...prev,
      [field]: isNaN(num) ? val : num
    }));
  };

  const handleSaveThresholds = (e) => {
    e.preventDefault();
    updateThresholds(draftThresholds);
    setSaveFeedback('CONFIGURATION APPLIED TO ACTIVE RUNTIME');
    setTimeout(() => setSaveFeedback(null), 3500);
  };

  const handleResetDefaults = () => {
    resetThresholds();
    setSaveFeedback('THRESHOLDS RESET TO POLAR DEFAULT MATRIX');
    setTimeout(() => setSaveFeedback(null), 3500);
  };

  const handleFullReset = () => {
    resetStationState();
    setSaveFeedback('STATION STATE FULLY REINITIALIZED TO NOMINAL BASELINE');
    setTimeout(() => setSaveFeedback(null), 3500);
  };

  // Clocks
  const utcString = currentTime.toLocaleTimeString('en-GB', {
    timeZone: 'UTC',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
  const localOffsetHours = config?.timeZoneOffsetHours ?? (activeStation === 'MAITRI' ? 1 : 5);
  const stationDate = new Date(currentTime.getTime() + localOffsetHours * 3600000);
  const localString = stationDate.toLocaleTimeString('en-GB', {
    timeZone: 'UTC',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });

  const lastUpdateFormatted = lastUpdated ? new Date(lastUpdated).toLocaleTimeString('en-GB', {
    timeZone: 'UTC',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }) + ' UTC' : 'Synchronized';

  return (
    <main className="main-viewport settings-viewport">
      {/* ── 0. PAGE HEADER & TECHNICAL STAMP ─────────────────────────────────── */}
      <section className="settings-page-header">
        <div>
          <div className="settings-kicker-strip">
            <span className="settings-kicker-tag">POLARIS CONTROL // CF-07</span>
            <span className="settings-env-badge badge-demo">DEMO CONFIGURATION</span>
            <span className="settings-env-badge badge-live">LIVE MEMORY BUS</span>
          </div>
          <h1 className="settings-title">MISSION CONFIGURATION CONSOLE</h1>
          <p className="settings-subtitle">
            Antarctic telemetry thresholds, power dispatch envelopes, satellite link parameters, and simulation state.
          </p>
        </div>

        <div className="settings-header-actions">
          <button 
            type="button" 
            className="settings-reset-all-btn"
            onClick={handleFullReset}
            title="Reset active scenario, thresholds, and sensor manual overrides"
          >
            RESET STATION STATE ↺
          </button>
        </div>
      </section>

      {/* FEEDBACK BANNER */}
      {saveFeedback && (
        <div className="settings-feedback-banner">
          <span className="feedback-check">✓</span>
          <span>{saveFeedback}</span>
        </div>
      )}

      <div className="settings-grid">
        {/* ── 1. STATION CONFIGURATION ────────────────────────────────────────── */}
        <section className="settings-card" aria-labelledby="section-station-cfg">
          <div className="settings-card-header">
            <div>
              <h2 id="section-station-cfg" className="settings-card-title">1. STATION IDENTITY & SPATIAL ANCHOR</h2>
              <span className="settings-card-desc">Active polar research facility and astronomical coordinate grid</span>
            </div>
            <span className="settings-status-pill pill-normal">ACTIVE</span>
          </div>

          <div className="settings-card-body">
            {/* Station Selector Instrument */}
            <div className="settings-station-selector-block">
              <span className="settings-field-label">ACTIVE STATION SELECTION:</span>
              <div className="settings-station-pills">
                <button
                  type="button"
                  className={`settings-station-pill ${activeStation === 'MAITRI' ? 'active' : ''}`}
                  onClick={() => setActiveStation('MAITRI')}
                >
                  <span className="pill-flag-dot" style={{ background: '#b65a1f' }} />
                  <span>MAITRI STATION (MTR)</span>
                </button>
                <button
                  type="button"
                  className={`settings-station-pill ${activeStation === 'BHARATI' ? 'active' : ''}`}
                  onClick={() => setActiveStation('BHARATI')}
                >
                  <span className="pill-flag-dot" style={{ background: '#3f6e4a' }} />
                  <span>BHARATI STATION (BHR)</span>
                </button>
              </div>
            </div>

            <div className="settings-specs-table">
              <div className="spec-row">
                <span className="spec-label">STATION ID</span>
                <span className="spec-val font-mono">{config.id || (activeStation === 'MAITRI' ? 'STN-IND-01' : 'STN-IND-02')}</span>
              </div>
              <div className="spec-row">
                <span className="spec-label">COORDINATES</span>
                <span className="spec-val font-mono">{config.coordinates || '70°45\'57"S, 11°44\'09"E'}</span>
              </div>
              <div className="spec-row">
                <span className="spec-label">ELEVATION</span>
                <span className="spec-val font-mono">{config.elevation || config.altitude || '117 m a.s.l.'}</span>
              </div>
              <div className="spec-row">
                <span className="spec-label">TIME CONFIGURATION</span>
                <span className="spec-val font-mono">
                  UTC: {utcString} | LOCAL: {localString} (UTC+{localOffsetHours})
                </span>
              </div>
              <div className="spec-row">
                <span className="spec-label">CONFIGURATION STATE</span>
                <span className="spec-val font-mono">
                  <span className="tag-inline-demo">IN-MEMORY STATE</span>
                  <span className="tag-inline-live">SHARED CONTEXT ACTIVE</span>
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* ── 2. ALERT OPERATIONAL THRESHOLDS ──────────────────────────────────── */}
        <section className="settings-card" aria-labelledby="section-alert-thresh">
          <div className="settings-card-header">
            <div>
              <h2 id="section-alert-thresh" className="settings-card-title">2. OPERATIONAL ALERT THRESHOLDS</h2>
              <span className="settings-card-desc">Safety envelopes for life-support, power bank depletion, and fuel reserve buffers</span>
            </div>
            <span className="settings-status-pill pill-demo">CONFIG ONLY</span>
          </div>

          <form className="settings-card-body" onSubmit={handleSaveThresholds}>
            <div className="thresholds-inputs-grid">
              {/* Battery Low */}
              <div className="threshold-field-group">
                <div className="field-meta">
                  <label htmlFor="thresh-battery-low" className="field-name">BATTERY CRITICAL LOW</label>
                  <span className="field-unit">% SOC</span>
                </div>
                <div className="field-input-wrap">
                  <input
                    id="thresh-battery-low"
                    type="number"
                    min="10"
                    max="80"
                    step="1"
                    className="field-input font-mono"
                    value={draftThresholds.batteryLowPct}
                    onChange={(e) => handleInputChange('batteryLowPct', e.target.value)}
                  />
                  <span className="field-input-adornment">%</span>
                </div>
                <span className="field-hint">Triggers AT RISK status & critical battery discharge alarms</span>
              </div>

              {/* Fuel Reserve Warning */}
              <div className="threshold-field-group">
                <div className="field-meta">
                  <label htmlFor="thresh-fuel-reserve" className="field-name">FUEL RESERVE BUFFER (LOW)</label>
                  <span className="field-unit">DAYS</span>
                </div>
                <div className="field-input-wrap">
                  <input
                    id="thresh-fuel-reserve"
                    type="number"
                    min="5"
                    max="60"
                    step="1"
                    className="field-input font-mono"
                    value={draftThresholds.fuelReserveDays}
                    onChange={(e) => handleInputChange('fuelReserveDays', e.target.value)}
                  />
                  <span className="field-input-adornment">days</span>
                </div>
                <span className="field-hint">Triggers LOW SUPPLIES status in Mission Readiness and Logistics</span>
              </div>

              {/* Generator Vibration Warning */}
              <div className="threshold-field-group">
                <div className="field-meta">
                  <label htmlFor="thresh-gen-vib-warn" className="field-name">GENERATOR VIBRATION (WARN)</label>
                  <span className="field-unit">mm/s</span>
                </div>
                <div className="field-input-wrap">
                  <input
                    id="thresh-gen-vib-warn"
                    type="number"
                    min="1.0"
                    max="6.0"
                    step="0.1"
                    className="field-input font-mono"
                    value={draftThresholds.generatorVibrationWarn}
                    onChange={(e) => handleInputChange('generatorVibrationWarn', e.target.value)}
                  />
                  <span className="field-input-adornment">mm/s</span>
                </div>
                <span className="field-hint">DG-2 rotor bearing harmonic warning advisory threshold</span>
              </div>

              {/* Generator Vibration Critical */}
              <div className="threshold-field-group">
                <div className="field-meta">
                  <label htmlFor="thresh-gen-vib-crit" className="field-name">GENERATOR VIBRATION (CRIT)</label>
                  <span className="field-unit">mm/s</span>
                </div>
                <div className="field-input-wrap">
                  <input
                    id="thresh-gen-vib-crit"
                    type="number"
                    min="2.0"
                    max="8.0"
                    step="0.1"
                    className="field-input font-mono"
                    value={draftThresholds.generatorVibrationCrit}
                    onChange={(e) => handleInputChange('generatorVibrationCrit', e.target.value)}
                  />
                  <span className="field-input-adornment">mm/s</span>
                </div>
                <span className="field-hint">Microgrid emergency automatic breaker trip limit</span>
              </div>

              {/* Temperature Warning */}
              <div className="threshold-field-group">
                <div className="field-meta">
                  <label htmlFor="thresh-temp-warn" className="field-name">EXTERIOR TEMP (WARNING)</label>
                  <span className="field-unit">°C</span>
                </div>
                <div className="field-input-wrap">
                  <input
                    id="thresh-temp-warn"
                    type="number"
                    min="-60.0"
                    max="0.0"
                    step="0.5"
                    className="field-input font-mono"
                    value={draftThresholds.tempWarningC}
                    onChange={(e) => handleInputChange('tempWarningC', e.target.value)}
                  />
                  <span className="field-input-adornment">°C</span>
                </div>
                <span className="field-hint">Habitation thermal transfer HVAC pre-heating trigger</span>
              </div>

              {/* Temperature Critical */}
              <div className="threshold-field-group">
                <div className="field-meta">
                  <label htmlFor="thresh-temp-crit" className="field-name">EXTERIOR TEMP (CRITICAL)</label>
                  <span className="field-unit">°C</span>
                </div>
                <div className="field-input-wrap">
                  <input
                    id="thresh-temp-crit"
                    type="number"
                    min="-80.0"
                    max="-20.0"
                    step="0.5"
                    className="field-input font-mono"
                    value={draftThresholds.tempCriticalC}
                    onChange={(e) => handleInputChange('tempCriticalC', e.target.value)}
                  />
                  <span className="field-input-adornment">°C</span>
                </div>
                <span className="field-hint">Deep cold emergency shelter lockdown procedure</span>
              </div>

              {/* Sensor Timeout */}
              <div className="threshold-field-group">
                <div className="field-meta">
                  <label htmlFor="thresh-sensor-timeout" className="field-name">TELEMETRY SENSOR TIMEOUT</label>
                  <span className="field-unit">SEC</span>
                </div>
                <div className="field-input-wrap">
                  <input
                    id="thresh-sensor-timeout"
                    type="number"
                    min="30"
                    max="600"
                    step="10"
                    className="field-input font-mono"
                    value={draftThresholds.sensorTimeoutSec}
                    onChange={(e) => handleInputChange('sensorTimeoutSec', e.target.value)}
                  />
                  <span className="field-input-adornment">sec</span>
                </div>
                <span className="field-hint">Bus heartbeat loss threshold before marking sensor OFFLINE</span>
              </div>
            </div>

            <div className="thresholds-form-footer">
              <span className="footer-persistence-note font-mono">
                PERSISTENCE: SESSION IN-MEMORY // NO FAKE BACKEND SYNC
              </span>
              <div className="thresholds-form-actions">
                <button
                  type="button"
                  className="btn-form-secondary"
                  onClick={handleResetDefaults}
                >
                  RESET DEFAULTS
                </button>
                <button
                  type="submit"
                  className="btn-form-primary"
                >
                  APPLY THRESHOLDS →
                </button>
              </div>
            </div>
          </form>
        </section>

        {/* ── 3. POWER CONFIGURATION ──────────────────────────────────────────── */}
        <section className="settings-card" aria-labelledby="section-power-cfg">
          <div className="settings-card-header">
            <div>
              <h2 id="section-power-cfg" className="settings-card-title">3. MICROGRID POWER ARCHITECTURE</h2>
              <span className="settings-card-desc">Generator operating envelopes, battery cutoffs, and load priority thresholds</span>
            </div>
            <span className="settings-status-pill pill-normal">NOMINAL</span>
          </div>

          <div className="settings-card-body">
            <div className="settings-specs-table">
              <div className="spec-row">
                <span className="spec-label">GENERATOR OPERATING LIMITS</span>
                <span className="spec-val font-mono">
                  {activeStation === 'MAITRI' ? 'DG-1: 45.0 kW | DG-2: 45.0 kW (Rated 1500 RPM)' : 'CHP Unit 1-3: 60.0 kW (Rated 1800 RPM)'}
                </span>
              </div>
              <div className="spec-row">
                <span className="spec-label">BATTERY MINIMUM SOC (BMS FLOOR)</span>
                <span className="spec-val font-mono">
                  {thresholds.minBatterySocPct}% (Current SOC: {telemetry.battery?.percentage ?? 78}%)
                </span>
              </div>
              <div className="spec-row">
                <span className="spec-label">BATTERY MAXIMUM SOC (ABSORPTION)</span>
                <span className="spec-val font-mono">
                  {thresholds.maxBatterySocPct}% (Float Voltage: {telemetry.battery?.voltage || '418.2 V'})
                </span>
              </div>
              <div className="spec-row">
                <span className="spec-label">CRITICAL LIFE-SUPPORT LOAD TIER</span>
                <span className="spec-val font-mono">
                  {thresholds.criticalLoadKw} kW (Current Total Demand: {telemetry.power?.currentPower || '84.3 kW'})
                </span>
              </div>
              <div className="spec-row">
                <span className="spec-label">MINIMUM RENEWABLE TARGET MIX</span>
                <span className="spec-val font-mono">
                  {thresholds.renewableContributionPct}% Solar/Wind Target (Connected to Energy dispatch)
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* ── 4. COMMUNICATIONS ──────────────────────────────────────────────── */}
        <section className="settings-card" aria-labelledby="section-comms-cfg">
          <div className="settings-card-header">
            <div>
              <h2 id="section-comms-cfg" className="settings-card-title">4. SATELLITE COMMUNICATIONS & TELEMETRY LINK</h2>
              <span className="settings-card-desc">Primary orbital transceiver, link margins, and telemetry protocol</span>
            </div>
            <span className={`settings-status-pill pill-${(telemetry.satellite?.status || 'ONLINE').toLowerCase()}`}>
              {telemetry.satellite?.status || 'ONLINE'}
            </span>
          </div>

          <div className="settings-card-body">
            <div className="settings-specs-table">
              <div className="spec-row">
                <span className="spec-label">SATELLITE LINK STATUS</span>
                <span className="spec-val font-mono">
                  {telemetry.satellite?.status || 'ONLINE'} (Signal: {telemetry.satellite?.signalQuality ?? 96}%)
                </span>
              </div>
              <div className="spec-row">
                <span className="spec-label">PRIMARY ORBITAL TRANSCEIVER</span>
                <span className="spec-val font-mono">
                  {telemetry.satellite?.satellite || (activeStation === 'MAITRI' ? 'GSAT-14 / Inmarsat-C' : 'GSAT-30 / Starlink Gateway')}
                </span>
              </div>
              <div className="spec-row">
                <span className="spec-label">LINK DROPOUT TIMEOUT</span>
                <span className="spec-val font-mono">120 Seconds (Auto-switch to HF burst backup)</span>
              </div>
              <div className="spec-row">
                <span className="spec-label">LAST SYNCHRONIZATION</span>
                <span className="spec-val font-mono">{lastUpdateFormatted}</span>
              </div>
            </div>

            {/* Cryptographic notice */}
            <div className="settings-secure-box">
              <div className="secure-box-header">
                <span className="secure-icon">🔒</span>
                <span className="secure-title">CONFIGURATION CONTROLLED BY DEPLOYMENT</span>
              </div>
              <p className="secure-desc">
                Cryptographic authentication keys, GSAT uplink transponder frequencies, and secure ground-station MQTT endpoints are sealed in mission hardware security modules (HSM). Runtime modification is restricted to authenticated mission commands.
              </p>
            </div>
          </div>
        </section>

        {/* ── 5. TELEMETRY & DATA ────────────────────────────────────────────── */}
        <section className="settings-card" aria-labelledby="section-telemetry-cfg">
          <div className="settings-card-header">
            <div>
              <h2 id="section-telemetry-cfg" className="settings-card-title">5. TELEMETRY BUS & SHARED STATE</h2>
              <span className="settings-card-desc">Real-time instrument synchronization parameters</span>
            </div>
            <span className="settings-status-pill pill-normal">SYNCHRONIZED</span>
          </div>

          <div className="settings-card-body">
            <div className="settings-specs-table">
              <div className="spec-row">
                <span className="spec-label">TELEMETRY BUS STATUS</span>
                <span className="spec-val font-mono">
                  <span className="status-dot-sm" style={{ background: 'var(--polaris-sage)' }} />
                  ONLINE // IN-MEMORY MULTI-ZONE STREAM
                </span>
              </div>
              <div className="spec-row">
                <span className="spec-label">DATA SOURCE ARCHITECTURE</span>
                <span className="spec-val font-mono">POLARIS SHARED StationContext (Single Source of Truth)</span>
              </div>
              <div className="spec-row">
                <span className="spec-label">TELEMETRY REFRESH CADENCE</span>
                <span className="spec-val font-mono">10,000 ms (10-second tick interval)</span>
              </div>
              <div className="spec-row">
                <span className="spec-label">LAST TELEMETRY UPDATE</span>
                <span className="spec-val font-mono">{lastUpdateFormatted}</span>
              </div>
              <div className="spec-row">
                <span className="spec-label">EVENTS MODULE CONNECTION</span>
                <span className="spec-val font-mono">CONNECTED (Synchronized with 16 expedition timeline items)</span>
              </div>
              <div className="spec-row">
                <span className="spec-label">DIGITAL TWIN CONNECTION</span>
                <span className="spec-val font-mono">SYNCHRONIZED (6 spatial BIM zones, camera targeting active)</span>
              </div>
            </div>
          </div>
        </section>

        {/* ── 6. DEMO & SCENARIO CONTROLS ────────────────────────────────────── */}
        <section className="settings-card" aria-labelledby="section-demo-cfg">
          <div className="settings-card-header">
            <div>
              <h2 id="section-demo-cfg" className="settings-card-title">6. SIMULATION & SCENARIO INJECTION</h2>
              <span className="settings-card-desc">Controlled operational anomaly injections for operator training and drills</span>
            </div>
            <span className={`settings-status-pill ${demoModeEnabled ? 'pill-demo' : 'pill-normal'}`}>
              DEMO: {demoModeEnabled ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>

          <div className="settings-card-body">
            <div className="settings-demo-toggle-row">
              <div>
                <span className="settings-field-label">DEMO MODE SIMULATION LAYER</span>
                <p className="settings-field-sub">Enables scenario injection dock across Dashboard, Twin, and Energy</p>
              </div>
              <button
                type="button"
                className={`settings-toggle-btn ${demoModeEnabled ? 'active' : ''}`}
                onClick={() => setDemoModeEnabled(prev => !prev)}
              >
                {demoModeEnabled ? 'DEMO MODE: ENABLED' : 'DEMO MODE: DISABLED'}
              </button>
            </div>

            {demoModeEnabled && (
              <div className="settings-scenario-controls-block">
                <span className="settings-field-label">ACTIVE DRILL SCENARIO (SHARED APPLICATION STATE):</span>
                <div className="scenario-pills-grid">
                  {Object.entries(DEMO_SCENARIOS).map(([key, scn]) => (
                    <button
                      key={key}
                      type="button"
                      className={`scenario-choice-btn ${scenario === key ? 'active' : ''}`}
                      onClick={() => setScenario(key)}
                    >
                      <span className="scenario-btn-label">{scn.label}</span>
                      <span className="scenario-btn-desc">{scn.badge}</span>
                    </button>
                  ))}
                </div>

                <div className="scenario-actions-bar">
                  <button
                    type="button"
                    className="btn-scenario-action"
                    onClick={() => setScenario('NORMAL')}
                  >
                    RESET SCENARIO TO NORMAL ↺
                  </button>
                  <button
                    type="button"
                    className="btn-scenario-action"
                    onClick={handleFullReset}
                  >
                    RESET STATION ENTIRE STATE ↺
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* ── 7. SYSTEM INFORMATION ──────────────────────────────────────────── */}
        <section className="settings-card" aria-labelledby="section-sys-info">
          <div className="settings-card-header">
            <div>
              <h2 id="section-sys-info" className="settings-card-title">7. POLARIS SYSTEM SPECIFICATIONS</h2>
              <span className="settings-card-desc">Software build, 3D parametric engine, and expedition registry</span>
            </div>
            <span className="settings-status-pill pill-normal">VERIFIED</span>
          </div>

          <div className="settings-card-body">
            <div className="settings-specs-table">
              <div className="spec-row">
                <span className="spec-label">POLARIS PLATFORM VERSION</span>
                <span className="spec-val font-mono">v2.6.4-polar // NCPOR Build 2026.09</span>
              </div>
              <div className="spec-row">
                <span className="spec-label">DIGITAL TWIN 3D ENGINE</span>
                <span className="spec-val font-mono">Three.js / React Three Fiber (Parametric BIM v2.1)</span>
              </div>
              <div className="spec-row">
                <span className="spec-label">EXPEDITION DATA MODEL</span>
                <span className="spec-val font-mono">45th Indian Scientific Expedition to Antarctica (ISEA)</span>
              </div>
              <div className="spec-row">
                <span className="spec-label">CURRENT ACTIVE STATION</span>
                <span className="spec-val font-mono">{activeStation} RESEARCH STATION ({config.shortCode || 'MTR'})</span>
              </div>
              <div className="spec-row">
                <span className="spec-label">LAST CONFIGURATION AUDIT</span>
                <span className="spec-val font-mono">{lastUpdateFormatted}</span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
};

export default Settings;
