import React from 'react';

export const TwinLegend = ({
  sensors = [],
  isHeatmapActive = false,
  isSystemActive = false,
  telemetry = {}
}) => {
  const total = sensors.length;
  const normal = sensors.filter((s) => s.status?.toUpperCase() === 'NORMAL').length;
  const warning = sensors.filter((s) => s.status?.toUpperCase() === 'WARNING').length;
  const critical = sensors.filter((s) => s.status?.toUpperCase() === 'CRITICAL').length;
  const offline = sensors.filter((s) => s.status?.toUpperCase() === 'OFFLINE').length;

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
            ? 'DYNAMIC SPATIAL HEATMAP'
            : 'SENSOR TELEMETRY STATUS'}
        </span>
        <span style={{ fontSize: '0.625rem', fontFamily: 'var(--font-mono)', color: 'var(--polaris-text-muted)' }}>
          {isSystemActive ? (power.currentPower || '84.3 kW LOAD') : `${total} TOTAL SENSORS`}
        </span>
      </div>

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

      {isHeatmapActive && (
        <div style={{ borderTop: '1px solid var(--polaris-border-subtle)', paddingTop: '0.35rem', marginTop: '0.15rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.5625rem', fontFamily: 'var(--font-mono)', color: 'var(--polaris-text-muted)', marginBottom: '0.2rem' }}>
            <span>LOW (NOMINAL)</span>
            <span>MEDIUM (WARNING)</span>
            <span>HIGH (CRITICAL)</span>
          </div>
          <div
            style={{
              height: '5px',
              borderRadius: '3px',
              background: 'linear-gradient(to right, rgba(63, 110, 74, 0.25) 0%, rgba(217, 130, 26, 0.65) 50%, rgba(200, 42, 42, 0.85) 100%)',
              border: '1px solid rgba(0, 0, 0, 0.08)'
            }}
          />
        </div>
      )}
    </div>
  );
};

export default TwinLegend;
