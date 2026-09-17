import React from 'react';

export const SensorDetailsPanel = ({ sensor, onClose }) => {
  if (!sensor) return null;

  const getStatusClass = (status) => {
    switch (status?.toUpperCase()) {
      case 'NORMAL': return 'normal';
      case 'WARNING': return 'warning';
      case 'CRITICAL': return 'critical';
      case 'OFFLINE': return 'offline';
      default: return 'unknown';
    }
  };

  const statusCls = getStatusClass(sensor.status);

  return (
    <div className="twin-detail-drawer" aria-label="3D Sensor Telemetry Inspection">
      <div className="twin-drawer-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.25rem' }}>
            <span className="sensor-domain-badge">{sensor.domain}</span>
            <span className={`sensor-status-indicator ${statusCls}`}>
              ● {sensor.status}
            </span>
          </div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--polaris-text-primary)' }}>
            {sensor.name}
          </h3>
          <span className="sensor-id-sub">STATION ASSET: {sensor.id}</span>
        </div>

        <button
          type="button"
          className="modal-close-btn"
          onClick={onClose}
          aria-label="Close sensor inspector"
        >
          ✕
        </button>
      </div>

      <div className="twin-drawer-body">
        {/* Value Callout */}
        <div className="sensor-hero-telemetry-banner" style={{ padding: '1rem' }}>
          <div>
            <div className="spec-label">LIVE READOUT</div>
            <div className="sensor-hero-reading" style={{ fontSize: '1.85rem' }}>
              {sensor.value}
              <span className="unit">{sensor.unit}</span>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div className="spec-label">SIGNAL QUALITY</div>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--status-normal)', fontSize: '0.85rem' }}>
              {sensor.quality || 'GOOD'}
            </span>
          </div>
        </div>

        {/* Technical Attributes Grid */}
        <div className="sensor-spec-grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '0.65rem 1rem' }}>
          <div className="spec-item">
            <span className="spec-label">TRANSDUCER TYPE</span>
            <span className="spec-value">{sensor.type || 'INSTRUMENT'}</span>
          </div>

          <div className="spec-item">
            <span className="spec-label">CRITICALITY</span>
            <span className="spec-value">{sensor.criticality || 'HIGH'}</span>
          </div>

          <div className="spec-item">
            <span className="spec-label">LAST TELEMETRY SYNC</span>
            <span className="spec-value">{sensor.lastUpdate || '19:28:09 UTC'}</span>
          </div>

          <div className="spec-item">
            <span className="spec-label">OPERATING RANGE</span>
            <span className="spec-value">{sensor.minValue ?? '-'} to {sensor.maxValue ?? '-'} {sensor.unit}</span>
          </div>

          <div className="spec-item" style={{ gridColumn: 'span 2' }}>
            <span className="spec-label">3D SPATIAL COORDINATES (X / Y / Z)</span>
            <span className="spec-value" style={{ color: 'var(--polaris-copper)' }}>
              X: {sensor.x} m &nbsp;|&nbsp; Y: {sensor.y} m &nbsp;|&nbsp; Z: {sensor.z} m
            </span>
          </div>
        </div>
      </div>

      <div className="twin-drawer-footer">
        <span style={{ fontSize: '0.65rem', fontFamily: 'var(--font-mono)', color: 'var(--polaris-text-muted)' }}>
          Active spatial telemetry beacon
        </span>
        <button
          type="button"
          className="modal-close-btn"
          onClick={onClose}
          style={{ width: 'auto', padding: '0.3rem 0.75rem', fontSize: '0.75rem' }}
        >
          DISMISS INSPECTOR
        </button>
      </div>
    </div>
  );
};

export default SensorDetailsPanel;
