import React from 'react';
import { useStationTelemetry } from '../hooks/useStationTelemetry';

export const ConnectionStatus = () => {
  const { telemetry } = useStationTelemetry();
  const conn = telemetry.connectivity || {};
  const isOnline = conn.status === 'ONLINE';

  return (
    <div className="satellite-indicator" title={`Uplink: ${conn.satellite || 'GSAT'} | Latency: ${conn.latency || '318ms'}`}>
      <div className="time-readout">
        <span className="time-label">SATELLITE UPLINK</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span className={`status-dot-sm ${isOnline ? '' : 'offline'}`} />
          <span style={{ fontWeight: 700, color: isOnline ? 'var(--status-normal)' : 'var(--status-critical)' }}>
            {isOnline ? 'ONLINE' : 'OFFLINE'}
          </span>
          <span style={{ color: 'var(--polaris-text-muted)', fontSize: '0.65rem' }}>
            ({conn.latency || '42 ms'})
          </span>
        </div>
      </div>
    </div>
  );
};

export default ConnectionStatus;
