import React from 'react';

export const TwinLegend = ({ sensors = [] }) => {
  const total = sensors.length;
  const normal = sensors.filter((s) => s.status?.toUpperCase() === 'NORMAL').length;
  const warning = sensors.filter((s) => s.status?.toUpperCase() === 'WARNING').length;
  const critical = sensors.filter((s) => s.status?.toUpperCase() === 'CRITICAL').length;
  const offline = sensors.filter((s) => s.status?.toUpperCase() === 'OFFLINE').length;

  const legendItems = [
    { label: 'TOTAL', color: '#191c20', count: total },
    { label: 'NORMAL', color: '#3f6e4a', count: normal },
    { label: 'WARNING', color: '#b26814', count: warning },
    { label: 'CRITICAL', color: '#b5382b', count: critical },
    { label: 'OFFLINE', color: '#5d6672', count: offline }
  ];

  return (
    <div className="twin-legend-panel">
      <span className="twin-legend-title">SENSOR TELEMETRY STATUS</span>
      <div className="twin-legend-items">
        {legendItems.map((item) => (
          <div className="twin-legend-item" key={item.label}>
            <span
              className="twin-legend-dot"
              style={{ background: item.color }}
            />
            <span className="twin-legend-label">
              {item.label} <strong style={{ marginLeft: '3px', color: '#191c20' }}>{item.count}</strong>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TwinLegend;
