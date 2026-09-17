import React from 'react';
import { useStationTelemetry } from '../hooks/useStationTelemetry';

export const MetricCard = () => {
  const { telemetry, alerts } = useStationTelemetry();
  const { power, battery, fuel, connectivity, satellite } = telemetry;
  const conn = satellite || connectivity || {};

  // Compute counts
  const criticalCount = alerts.filter(a => a.severity === 'CRITICAL').length;
  const warningCount = alerts.filter(a => a.severity === 'WARNING').length;
  const totalAlertsStr = String(alerts.length).padStart(2, '0');
  const criticalStr = String(criticalCount).padStart(2, '0');
  const warningStr = String(warningCount).padStart(2, '0');

  // Fallback sparkline points
  const defaultSparkline = "0,28 15,24 30,26 45,18 60,14 75,19 90,12 105,16 120,8 135,11 150,6";
  const activeSparkline = power?.sparklinePoints || defaultSparkline;

  const isOnline = conn?.status === 'ONLINE';

  return (
    <div className="systems-grid-layout" aria-label="Station Key Systems">
      {/* 1. POWER SYSTEM — Primary Focal Weight */}
      <div className="system-card-power" id="system-power-hero">
        <div>
          <div className="system-title-tag">
            <span>POWER SYSTEM</span>
            <span style={{ color: 'var(--polaris-copper)', fontWeight: 700 }}>MICROGRID ACTIVE</span>
          </div>

          <div className="hero-metric-readout">
            {power?.currentPower?.split(' ')[0] || '84.3'}
            <span className="unit">kW</span>
          </div>

          {/* Small 24-hour Trend Sparkline */}
          <div style={{ margin: '0.75rem 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.625rem', fontFamily: 'var(--font-mono)', color: 'var(--polaris-text-muted)', marginBottom: '0.2rem' }}>
              <span>24H LOAD PROFILE</span>
              <span>PEAK: {power?.peakLoad || '89.2 kW'}</span>
            </div>
            <svg width="100%" height="32" viewBox="0 0 150 32" preserveAspectRatio="none" style={{ overflow: 'visible' }}>
              <polyline
                fill="none"
                stroke="var(--polaris-copper)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={activeSparkline}
              />
            </svg>
          </div>
        </div>

        {/* Generation Breakdown */}
        <div className="generation-breakdown-table">
          <div className="gen-row">
            <span className="gen-label">
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--polaris-copper)' }} />
              SOLAR
            </span>
            <span className="gen-val">{power?.solarGeneration || '42.8 kW'}</span>
          </div>

          <div className="gen-row">
            <span className="gen-label">
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--polaris-sage)' }} />
              WIND
            </span>
            <span className="gen-val">{power?.windGeneration || '18.4 kW'}</span>
          </div>

          <div className="gen-row">
            <span className="gen-label">
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--polaris-text-muted)' }} />
              DIESEL
            </span>
            <span className="gen-val">{power?.dieselGeneration || '23.1 kW'}</span>
          </div>
        </div>
      </div>

      {/* 2. BATTERY SYSTEM */}
      <div className="system-module-secondary">
        <div>
          <div className="system-title-tag">
            <span>BATTERY</span>
            <span style={{ color: 'var(--polaris-sage)', fontWeight: 700 }}>
              {battery?.state || 'CHARGING'}
            </span>
          </div>

          <div className="metric-medium-readout">
            {battery?.percentage || 78}
            <span className="unit">%</span>
          </div>

          {/* Energy Flow Visualization */}
          <div className="energy-flow-track" title="Substation charge buffer flow">
            <div 
              className="energy-flow-fill"
              style={{ 
                width: `${battery?.percentage || 78}%`,
                background: (battery?.percentage || 78) > 30 ? 'var(--polaris-sage)' : 'var(--status-critical)'
              }}
            />
          </div>
        </div>

        <div className="metric-sub-descriptor">
          <span style={{ color: 'var(--polaris-text-muted)' }}>EST. REMAINING</span>
          <span style={{ fontWeight: 600 }}>{battery?.remainingHours || '38.5 hrs'}</span>
        </div>
      </div>

      {/* 3. FUEL RESERVE */}
      <div className="system-module-secondary">
        <div>
          <div className="system-title-tag">
            <span>FUEL RESERVE</span>
            <span style={{ color: 'var(--polaris-text-muted)' }}>STORAGE</span>
          </div>

          <div className="metric-medium-readout">
            {fuel?.currentLevel || 64}
            <span className="unit">%</span>
          </div>
        </div>

        <div className="metric-sub-descriptor">
          <span style={{ color: 'var(--polaris-text-muted)' }}>AUTONOMY</span>
          <span style={{ fontWeight: 700, color: 'var(--polaris-copper)' }}>
            EST. {fuel?.remainingDays ? `${fuel.remainingDays} DAYS` : '18.4 DAYS'}
          </span>
        </div>
      </div>

      {/* 4. SATELLITE LINK */}
      <div className="system-module-secondary">
        <div>
          <div className="system-title-tag">
            <span>SATELLITE LINK</span>
            <span style={{ color: isOnline ? 'var(--status-normal)' : 'var(--status-critical)', fontWeight: 700 }}>
              {isOnline ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>

          <div className="metric-medium-readout" style={{ fontSize: '1.45rem' }}>
            {conn?.latency || '42 ms'}
          </div>
        </div>

        <div className="metric-sub-descriptor">
          <span style={{ color: 'var(--polaris-text-muted)' }}>UPLINK</span>
          <span style={{ fontWeight: 600 }}>{conn?.satellite?.split('/')[0] || 'GSAT-14'}</span>
        </div>
      </div>

      {/* 5. ALERT LOAD */}
      <div className="system-module-secondary">
        <div>
          <div className="system-title-tag">
            <span>ALERT LOAD</span>
            <span style={{ color: criticalCount > 0 ? 'var(--status-critical)' : 'var(--polaris-sage)', fontWeight: 700 }}>
              {criticalCount > 0 ? 'ATTENTION' : 'NOMINAL'}
            </span>
          </div>

          <div className="metric-medium-readout">
            {totalAlertsStr}
            <span className="unit">TOTAL</span>
          </div>
        </div>

        <div className="metric-sub-descriptor">
          <span style={{ color: 'var(--status-critical)', fontWeight: 600 }}>
            {criticalStr} CRITICAL
          </span>
          <span style={{ color: 'var(--status-warning)', fontWeight: 600 }}>
            {warningStr} WARNING
          </span>
        </div>
      </div>
    </div>
  );
};

export default MetricCard;
