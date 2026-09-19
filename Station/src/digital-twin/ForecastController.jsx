import React, { useEffect, useRef, useState } from 'react';

/**
 * ForecastController
 *
 * Operational forward projection timeline controller for Digital Twin.
 * Supports 7, 30, and 90-day projection horizons with scrubber slider,
 * playback animation, and projected resource summaries.
 */
export const ForecastController = ({
  stationCode = 'MTR',
  horizonDays = 30,
  onHorizonChange,
  dayOffset = 0,
  onDayOffsetChange,
  forecastResult
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const playTimerRef = useRef(null);

  // Auto playback loop
  useEffect(() => {
    if (!isPlaying) {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
      return;
    }

    playTimerRef.current = setInterval(() => {
      onDayOffsetChange((prev) => {
        const step = horizonDays === 7 ? 0.25 : horizonDays === 30 ? 1 : 2;
        const next = prev + step;
        if (next >= horizonDays) {
          setIsPlaying(false);
          return horizonDays;
        }
        return next;
      });
    }, 280);

    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    };
  }, [isPlaying, horizonDays, onDayOffsetChange]);

  const isLive = dayOffset === 0;
  const isInsufficient = forecastResult?.isInsufficient;

  const fuel = forecastResult?.fuel || {};
  const battery = forecastResult?.battery || {};
  const power = forecastResult?.power || {};

  // Status color mappings
  const getStatusColor = (status) => {
    switch ((status || '').toUpperCase()) {
      case 'CRITICAL':
      case 'CRITICAL EMERGENCY':
        return 'var(--polaris-red)';
      case 'WARNING':
      case 'LOAD SHEDDING':
        return 'var(--polaris-amber)';
      case 'NORMAL':
      case 'NOMINAL':
      case 'STABLE':
      case 'SECURE':
      case 'OPTIMAL':
        return 'var(--polaris-green)';
      default:
        return 'var(--polaris-text-muted)';
    }
  };

  const handleStep = (delta) => {
    setIsPlaying(false);
    onDayOffsetChange((prev) => Math.max(0, Math.min(horizonDays, +(prev + delta).toFixed(1))));
  };

  const handleResetLive = () => {
    setIsPlaying(false);
    onDayOffsetChange(0);
  };

  // Timeline key milestone markers based on horizon
  const milestones = horizonDays === 7 ? [
    { day: 0, label: 'T+0 (LIVE)' },
    { day: 2, label: 'T+2d' },
    { day: 4, label: 'T+4d' },
    { day: 7, label: 'T+7d (WEEK 1)' }
  ] : horizonDays === 30 ? [
    { day: 0, label: 'T+0 (LIVE)' },
    { day: 7, label: 'T+7d' },
    { day: 14, label: 'T+14d (RESUPPLY)' },
    { day: 21, label: 'T+21d' },
    { day: 30, label: 'T+30d (1 MO)' }
  ] : [
    { day: 0, label: 'T+0 (LIVE)' },
    { day: 15, label: 'T+15d' },
    { day: 30, label: 'T+30d' },
    { day: 60, label: 'T+60d' },
    { day: 90, label: 'T+90d (Q1)' }
  ];

  return (
    <div className="forecast-controller-dock" role="region" aria-label="Forecast Timeline Controller">
      {/* ── Top Header: Mode & Horizon Selector ── */}
      <div className="forecast-dock-header">
        <div className="forecast-title-group">
          <span className="forecast-dock-title">OPERATIONAL RESOURCE PROJECTION</span>
          <span className={`forecast-state-badge ${isLive ? 'live' : 'forecast'}`}>
            {isLive ? '● LIVE STATE' : `🔮 FORECAST: T+${dayOffset.toFixed(1)} DAYS`}
          </span>
          <span className="forecast-station-tag">
            STATION: {stationCode}
          </span>
        </div>

        {/* Horizon Picker */}
        <div className="forecast-horizon-strip" role="group" aria-label="Select Forecast Horizon">
          <span className="forecast-strip-label">HORIZON:</span>
          {[7, 30, 90].map((h) => (
            <button
              key={h}
              type="button"
              className={`forecast-horizon-btn ${horizonDays === h ? 'active' : ''}`}
              onClick={() => {
                onHorizonChange(h);
                if (dayOffset > h) onDayOffsetChange(h);
              }}
            >
              {h} DAYS
            </button>
          ))}
        </div>
      </div>

      {isInsufficient ? (
        <div className="forecast-insufficient-notice">
          <span style={{ color: 'var(--polaris-amber)' }}>⚠️</span>
          <strong>DATA INSUFFICIENT</strong> — Baseline consumption or capacity telemetry not available for forward projection.
        </div>
      ) : (
        <>
          {/* ── Center: Interactive Timeline Scrubber ── */}
          <div className="forecast-timeline-wrapper">
            <div className="forecast-playback-controls">
              <button
                type="button"
                className="forecast-ctrl-btn"
                onClick={handleResetLive}
                title="Reset to Live State (Day 0)"
              >
                LIVE (0d)
              </button>
              <button
                type="button"
                className="forecast-ctrl-btn"
                onClick={() => handleStep(-1)}
                title="Step backward 1 day"
                disabled={dayOffset <= 0}
              >
                ◀ -1D
              </button>
              <button
                type="button"
                className={`forecast-ctrl-btn ${isPlaying ? 'active' : ''}`}
                onClick={() => setIsPlaying(!isPlaying)}
                title={isPlaying ? 'Pause forecast timeline' : 'Play forecast timeline'}
              >
                {isPlaying ? '⏸ PAUSE' : '▶ PLAY'}
              </button>
              <button
                type="button"
                className="forecast-ctrl-btn"
                onClick={() => handleStep(1)}
                title="Step forward 1 day"
                disabled={dayOffset >= horizonDays}
              >
                +1D ▶
              </button>
            </div>

            {/* Slider track */}
            <div className="forecast-slider-container">
              <input
                type="range"
                min={0}
                max={horizonDays}
                step={0.5}
                value={dayOffset}
                onChange={(e) => {
                  setIsPlaying(false);
                  onDayOffsetChange(Number(e.target.value));
                }}
                className="forecast-range-slider"
                aria-label="Forecast day scrubber"
              />

              {/* Milestone labels */}
              <div className="forecast-milestones-row">
                {milestones.map((m) => (
                  <span
                    key={m.day}
                    className={`forecast-milestone-label ${Math.abs(dayOffset - m.day) < 1.5 ? 'current' : ''}`}
                    style={{ left: `${(m.day / horizonDays) * 100}%` }}
                    onClick={() => {
                      setIsPlaying(false);
                      onDayOffsetChange(m.day);
                    }}
                  >
                    {m.label}
                  </span>
                ))}
              </div>
            </div>

            <div className="forecast-time-readout">
              <span className="readout-date">{forecastResult?.projectedDateFormatted || 'PROJECTED TIME'}</span>
              <span className="readout-offset">+{dayOffset.toFixed(1)}d of {horizonDays}d</span>
            </div>
          </div>

          {/* ── Bottom: Projected Resource KPI Strip ── */}
          <div className="forecast-kpi-grid">
            {/* 1. Fuel Reserve */}
            <div className="forecast-kpi-card">
              <span className="kpi-label">DIESEL / FUEL RESERVE</span>
              <div className="kpi-val-row">
                <span className="kpi-val">{fuel.percentage ?? '—'}%</span>
                <span className="kpi-sub">({fuel.liters?.toLocaleString() ?? '—'} L)</span>
              </div>
              <div className="kpi-status-row">
                <span className="kpi-status-dot" style={{ background: getStatusColor(fuel.status) }} />
                <span style={{ color: getStatusColor(fuel.status), fontWeight: 700 }}>
                  {fuel.status || 'NOMINAL'}
                </span>
                <span className="kpi-meta">Burn: {fuel.dailyBurnRate} L/d</span>
              </div>
            </div>

            {/* 2. Fuel Autonomy */}
            <div className="forecast-kpi-card">
              <span className="kpi-label">FUEL AUTONOMY</span>
              <div className="kpi-val-row">
                <span className="kpi-val mono-val">{fuel.daysRemaining ?? '—'}</span>
                <span className="kpi-sub">DAYS REMAINING</span>
              </div>
              <div className="kpi-status-row">
                <span className="kpi-meta">
                  {fuel.daysRemaining <= 0
                    ? '⚠️ DEPLETED WITHOUT RESUPPLY'
                    : fuel.daysRemaining < 14
                    ? 'CRITICAL RESERVE WINDOW'
                    : 'WITHIN OPERATIONAL BUFFER'}
                </span>
              </div>
            </div>

            {/* 3. Battery Level */}
            <div className="forecast-kpi-card">
              <span className="kpi-label">BATTERY STORAGE</span>
              <div className="kpi-val-row">
                <span className="kpi-val">{battery.percentage ?? '—'}%</span>
                <span className="kpi-sub">({battery.voltage ?? '—'})</span>
              </div>
              <div className="kpi-status-row">
                <span className="kpi-status-dot" style={{ background: getStatusColor(battery.state === 'DISCHARGING' ? 'WARNING' : 'NORMAL') }} />
                <span style={{ fontWeight: 600 }}>{battery.state || 'FLOAT'}</span>
                <span className="kpi-meta">Health: {battery.health}</span>
              </div>
            </div>

            {/* 4. Energy State */}
            <div className="forecast-kpi-card">
              <span className="kpi-label">MICROGRID STATE</span>
              <div className="kpi-val-row">
                <span className="kpi-val" style={{ color: getStatusColor(power.energyStatus), fontSize: '0.88rem' }}>
                  {power.energyStatus || 'STABLE'}
                </span>
              </div>
              <div className="kpi-status-row">
                <span className="kpi-meta">Load: {power.loadPercentage}% capacity</span>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Footer architecture note */}
      <div className="forecast-dock-footer">
        <span>Deterministic forward projection based on active station telemetry. Architecture ready for Person C ML model integration.</span>
      </div>
    </div>
  );
};

export default ForecastController;
