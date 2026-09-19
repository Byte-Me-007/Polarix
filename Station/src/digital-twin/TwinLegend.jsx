import React from 'react';
import { isSensorMatchingMetric } from './SpatialHeatmap';

const METRIC_LABELS = {
  ALL: { name: 'ALL TELEMETRY', unit: '0.0 - 1.0 Norm' },
  TEMPERATURE: { name: 'TEMPERATURE', unit: '°C' },
  WIND: { name: 'WIND SPEED', unit: 'km/h' },
  POWER: { name: 'POWER & LOAD', unit: 'kW / Generation' },
  STRUCTURAL: { name: 'STRUCTURAL LOAD', unit: 'Strain / Displacement' },
  FUEL: { name: 'FUEL & LOGISTICS', unit: '% Level / Flow' }
};

export const TwinLegend = ({
  sensors = [],
  isHeatmapActive = false,
  isSystemActive = false,
  telemetry = {},
  heatmapMetric = 'TEMPERATURE'
}) => {
  const metricInfo = METRIC_LABELS[heatmapMetric] || { name: heatmapMetric, unit: 'Telemetry' };

  // Filter sensors for the active heatmap metric if heatmap mode is active
  const relevantSensors = isHeatmapActive
    ? sensors.filter(s => isSensorMatchingMetric(s, heatmapMetric))
    : sensors;

  const total = relevantSensors.length;
  const normal = relevantSensors.filter((s) => s.status?.toUpperCase() === 'NORMAL').length;
  const warning = relevantSensors.filter((s) => s.status?.toUpperCase() === 'WARNING').length;
  const critical = relevantSensors.filter((s) => s.status?.toUpperCase() === 'CRITICAL').length;
  const offline = relevantSensors.filter((s) => s.status?.toUpperCase() === 'OFFLINE').length;

  const power = telemetry?.power || {};
  const battery = telemetry?.battery || {};

  const legendItems = [
    { label: 'NORMAL', color: '#3f6e4a', count: normal },
    { label: 'WARNING', color: '#d9821a', count: warning },
    { label: 'CRITICAL', color: '#c82a2a', count: critical },
    { label: 'OFFLINE', color: '#727b87', count: offline }
  ];

  const systemLegendItems = [
    { label: 'SOLAR FLOW', color: '#d97706', value: power.solarGeneration || '42.8 kW' },
    { label: 'WIND FLOW',  color: '#4f6f52', value: power.windGeneration || '18.4 kW' },
    { label: 'DIESEL FLOW',color: '#b65a1f', value: power.dieselGeneration || '23.1 kW' },
    { label: 'BATTERY',    color: battery.state?.includes('DISCHARG') ? '#d97706' : '#4f6f52', value: `${battery.percentage ?? 78}%` }
  ];

  return (
    <div className="twin-legend-panel">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
        <span className="twin-legend-title">
          {isSystemActive
            ? 'SYSTEM POWER FLOW TOPOLOGY'
            : isHeatmapActive
            ? `TELEMETRY INTENSITY — ${metricInfo.name}`
            : 'SENSOR TELEMETRY STATUS'}
        </span>
        <span style={{ fontSize: '0.625rem', fontFamily: 'var(--font-mono)', color: 'var(--polaris-text-muted)' }}>
          {isSystemActive
            ? (power.currentPower || '84.3 kW LOAD')
            : isHeatmapActive
            ? `${total} ACTIVE SENSORS (${metricInfo.unit})`
            : `${total} TOTAL SENSORS`}
        </span>
      </div>

      {isHeatmapActive ? (
        <div style={{ marginTop: '0.4rem' }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.58rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--polaris-text-secondary)',
            marginBottom: '0.25rem'
          }}>
            <span style={{ fontWeight: 600, color: 'rgb(43, 92, 143)' }}>LOW</span>
            <span style={{ color: 'var(--polaris-text-muted)', letterSpacing: '2px' }}>─────────</span>
            <span style={{ fontWeight: 600, color: 'rgb(56, 142, 142)' }}>MEDIUM</span>
            <span style={{ color: 'var(--polaris-text-muted)', letterSpacing: '2px' }}>─────────</span>
            <span style={{ fontWeight: 600, color: 'rgb(217, 130, 26)' }}>HIGH</span>
            <span style={{ color: 'var(--polaris-text-muted)', letterSpacing: '2px' }}>─────────</span>
            <span style={{ fontWeight: 600, color: 'rgb(200, 42, 42)' }}>CRITICAL</span>
          </div>

          <div
            style={{
              height: '7px',
              borderRadius: '3px',
              background: 'linear-gradient(to right, rgb(43, 92, 143) 0%, rgb(56, 142, 142) 33%, rgb(217, 130, 26) 66%, rgb(200, 42, 42) 100%)',
              border: '1px solid rgba(0, 0, 0, 0.12)',
              boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.1)'
            }}
          />

          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: '0.5rem',
            marginTop: '0.45rem',
            paddingTop: '0.35rem',
            borderTop: '1px solid var(--polaris-border-subtle)',
            fontSize: '0.6rem',
            fontFamily: 'var(--font-mono)'
          }}>
            <span style={{ color: '#3f6e4a' }}>NOMINAL: <strong>{normal}</strong></span>
            <span style={{ color: '#d9821a' }}>WARNING: <strong>{warning}</strong></span>
            <span style={{ color: '#c82a2a' }}>CRITICAL: <strong>{critical}</strong></span>
            <span style={{ color: '#727b87' }}>OFFLINE: <strong>{offline}</strong></span>
          </div>
        </div>
      ) : (
        <div className="twin-legend-items">
          {(isSystemActive ? systemLegendItems : legendItems).map((item) => (
            <div className="twin-legend-item" key={item.label}>
              <span
                className="twin-legend-dot"
                style={{ background: item.color }}
              />
              <span className="twin-legend-label">
                {item.label} <strong style={{ marginLeft: '4px', color: 'var(--polaris-text-primary)' }}>{item.count !== undefined ? item.count : item.value}</strong>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TwinLegend;
