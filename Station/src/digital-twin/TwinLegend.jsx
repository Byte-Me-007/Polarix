import React from 'react';

export const TwinLegend = () => {
  const legendItems = [
    { label: 'NORMAL', color: 'var(--status-normal)', count: 'Nominal' },
    { label: 'WARNING', color: 'var(--status-warning)', count: 'Caution' },
    { label: 'CRITICAL', color: 'var(--status-critical)', count: 'Urgent' },
    { label: 'OFFLINE', color: 'var(--status-offline)', count: 'No Signal' }
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
            <span className="twin-legend-label">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TwinLegend;
