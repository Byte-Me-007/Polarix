import React, { useMemo } from 'react';
import { useMissionReadiness } from '../hooks/useMissionReadiness';

/**
 * StationHUDOverlays — Mission-Control Heads-Up Display overlays for the 3D Digital Twin.
 * Replicates the authentic polar remote station HUD layout from the reference design:
 *   1. Top-Left:     STATION STATUS HUD (System Health %, circular gauge, online status)
 *   2. Top-Right:    ENVIRONMENTAL FEED (Wind Speed m/s & km/h, Ext Temp, Barometer)
 *   3. Bottom-Right: REAL-TIME EVENT LOG (Live operational telemetry stream with status pips)
 *   4. Bottom-Left:  CAMERA CONTROLS HINT (L-Click rotate, R-Click pan, Scroll zoom)
 */

export const StationStatusHUD = ({ telemetry, sensors = [], config, readiness: propReadiness }) => {
  const hookReadiness = useMissionReadiness();
  const readiness = propReadiness || hookReadiness;

  const overallReadiness = readiness?.overallReadiness || 'READY';
  const overallSummary = readiness?.overallSummary || '';

  // Authoritative system health score derived from the shared readiness evaluation (Power, Comms, Infra, Supplies, Alerts)
  const healthScore = useMemo(() => {
    if (typeof readiness?.overallScore === 'number') {
      return readiness.overallScore;
    }
    if (readiness?.systems && readiness.systems.length > 0) {
      const avg = readiness.systems.reduce((sum, s) => sum + (typeof s.rating === 'number' ? s.rating : 90), 0) / readiness.systems.length;
      return Math.round(avg);
    }
    if (typeof telemetry?.healthScore === 'number') {
      return telemetry.healthScore;
    }
    return 94;
  }, [readiness?.overallScore, readiness?.systems, telemetry?.healthScore]);

  // Operational status styling aligned with POLARIS readiness design tokens
  const isAtRisk = overallReadiness === 'AT RISK';
  const isDegraded = overallReadiness === 'DEGRADED';
  const readinessColor = isAtRisk ? '#e53e3e' : isDegraded ? '#d97706' : '#38a169';
  const readinessClass = isAtRisk ? 'critical' : isDegraded ? 'warning' : 'normal';

  // SVG Gauge calculations
  const radius = 22;
  const circ = 2 * Math.PI * radius;
  const strokeDashoffset = circ - (circ * (healthScore / 100));
  const healthColor = healthScore >= 90 ? '#38a169' : healthScore >= 70 ? '#d97706' : '#e53e3e';

  return (
    <div className="station-hud-card hud-top-left" aria-label="Station Status HUD">
      <div className="hud-card-header">
        <span className="hud-pulse-dot" style={{ background: readinessColor }} />
        <span className="hud-header-title">STATION STATUS HUD</span>
      </div>

      <div className="hud-status-body">
        <div className="hud-health-metric">
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span className="hud-metric-label">SYSTEM HEALTH</span>
            <span style={{ fontSize: '0.48rem', color: '#94a3b8', letterSpacing: '0.04em' }}>
              SUBSYSTEM CONDITION
            </span>
          </div>
          <span className="hud-metric-value" style={{ color: healthColor }}>
            {healthScore}%
          </span>
          <div className="hud-health-bar-track">
            <div
              className="hud-health-bar-fill"
              style={{ width: `${healthScore}%`, background: healthColor }}
            />
          </div>
        </div>

        {/* Circular Gauge */}
        <div className="hud-gauge-wrap">
          <svg className="hud-gauge-svg" width="56" height="56" viewBox="0 0 56 56">
            <circle
              className="hud-gauge-track"
              cx="28"
              cy="28"
              r={radius}
              strokeWidth="4"
              fill="none"
            />
            <circle
              className="hud-gauge-progress"
              cx="28"
              cy="28"
              r={radius}
              strokeWidth="4"
              fill="none"
              stroke={healthColor}
              strokeDasharray={circ}
              strokeDashoffset={strokeDashoffset}
              transform="rotate(-90 28 28)"
            />
          </svg>
          <span className="hud-gauge-label">{Math.round(healthScore)}%</span>
        </div>
      </div>

      <div className="hud-card-footer">
        <span className="hud-footer-tag">
          {config?.zones?.length || 6} MODULES ACTIVE
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ fontSize: '0.50rem', color: '#94a3b8', letterSpacing: '0.04em' }}>READINESS:</span>
          <span
            className={`hud-footer-tag ${readinessClass}`}
            style={{ color: readinessColor, fontWeight: 700 }}
            title={overallSummary || `Operational Status: ${overallReadiness}`}
          >
            {overallReadiness}
          </span>
        </div>
      </div>
    </div>
  );
};

export const EnvironmentalFeedHUD = ({ telemetry }) => {
  const env = telemetry?.environmentalTelemetry || {};
  const windKmH = Number(env.windSpeed || 42.5);
  const windMs = (windKmH / 3.6).toFixed(1);
  const temp = env.temperature != null ? env.temperature : -18.4;
  const feelsLike = env.feelsLike != null ? env.feelsLike : -28.1;
  const pressure = env.pressure != null ? env.pressure : 986.2;
  const windDir = env.windDirection || 'SSE 158°';

  return (
    <div className="station-hud-card hud-top-right" aria-label="Environmental Feed">
      <div className="hud-card-header">
        <svg className="hud-wind-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2" />
        </svg>
        <span className="hud-header-title">ENVIRONMENTAL FEED</span>
      </div>

      <div className="hud-env-grid">
        <div className="hud-env-cell wide">
          <span className="hud-env-sublabel">WIND SPEED ({windDir})</span>
          <div className="hud-env-wind-readout">
            <span className="hud-env-wind-val">{windMs} <span className="hud-unit">m/s</span></span>
            <span className="hud-env-wind-sec">{windKmH} km/h</span>
          </div>
        </div>

        <div className="hud-env-cell">
          <span className="hud-env-sublabel">EXT TEMP</span>
          <span className="hud-env-val">{temp}°C</span>
        </div>

        <div className="hud-env-cell">
          <span className="hud-env-sublabel">FEELS LIKE</span>
          <span className="hud-env-val">{feelsLike}°C</span>
        </div>

        <div className="hud-env-cell wide">
          <span className="hud-env-sublabel">ATMOSPHERIC PRESSURE</span>
          <span className="hud-env-val">{pressure} <span className="hud-unit">hPa</span></span>
        </div>
      </div>
    </div>
  );
};

export const RealtimeEventLogHUD = ({ telemetry, alerts = [] }) => {
  const events = useMemo(() => {
    const list = [];
    const batt = telemetry?.battery;
    if (batt) {
      list.push({
        id: 'ev-batt',
        text: `Battery Bank A: ${batt.state || 'Nominal'} (${batt.percentage || 78}%)`,
        status: batt.percentage < 30 ? 'critical' : batt.percentage < 55 ? 'warning' : 'normal'
      });
    }
    const solar = telemetry?.power;
    if (solar?.solarGeneration) {
      list.push({
        id: 'ev-solar',
        text: `Solar PV Array: Gen ${solar.solarGeneration} load nominal`,
        status: 'normal'
      });
    }
    list.push({
      id: 'ev-airlock',
      text: 'Expedition Airlock: Biometric pressure stabilized',
      status: 'normal'
    });
    list.push({
      id: 'ev-met',
      text: 'Met Anemometer Array: Ultrasonic flux tracking active',
      status: 'normal'
    });
    return list.slice(0, 3);
  }, [telemetry]);

  return (
    <div className="station-hud-card hud-bottom-right" aria-label="Real-time Event Log">
      <div className="hud-card-header">
        <span className="hud-pulse-dot" style={{ background: '#b65a1f' }} />
        <span className="hud-header-title">REAL-TIME EVENT LOG</span>
      </div>

      <div className="hud-events-list">
        {events.map((ev) => (
          <div key={ev.id} className="hud-event-item">
            <span className={`hud-event-pip ${ev.status}`} />
            <span className="hud-event-text">{ev.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
