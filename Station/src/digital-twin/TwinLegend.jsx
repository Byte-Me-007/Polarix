import React from 'react';

export const TwinLegend = ({ sensors = [], isHeatmapActive = false }) => {
  const total = sensors.length;
  const normal = sensors.filter((s) => s.status?.toUpperCase() === 'NORMAL').length;
  const warning = sensors.filter((s) => s.status?.toUpperCase() === 'WARNING').length;
  const critical = sensors.filter((s) => s.status?.toUpperCase() === 'CRITICAL').length;
  const offline = sensors.filter((s) => s.status?.toUpperCase() === 'OFFLINE').length;

  const legendItems = [
    { label: 'NORMAL', color: '#3f6e4a', count: normal },
    { label: 'WARNING', color: '#d9821a', count: warning },
    { label: 'CRITICAL', color: '#c82a2a', count: critical },
    { label: 'OFFLINE', color: '#727b87', count: offline }
  ];

  return (
    <div className="twin-legend-panel">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
        <span className="twin-legend-title">
          {isHeatmapActive ? 'DYNAMIC SPATIAL HEATMAP' : 'SENSOR TELEMETRY STATUS'}
        </span>
        <span style={{ fontSize: '0.625rem', fontFamily: 'var(--font-mono)', color: 'var(--polaris-text-muted)' }}>
          {total} TOTAL SENSORS
        </span>
      </div>

      <div className="twin-legend-items">
        {legendItems.map((item) => (
          <div className="twin-legend-item" key={item.label}>
            <span
              className="twin-legend-dot"
              style={{ background: item.color }}
            />
            <span className="twin-legend-label">
              {item.label} <strong style={{ marginLeft: '2px', color: 'var(--polaris-text-primary)' }}>{item.count}</strong>
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
