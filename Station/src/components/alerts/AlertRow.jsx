import React from 'react';

/**
 * AlertRow
 * Operational alert card rendering severity indicator, metadata, anomaly score,
 * and direct operational actions: ACKNOWLEDGE and LOCATE IN DIGITAL TWIN.
 */
export const AlertRow = ({ alert, onAcknowledge, onLocate }) => {
  const isAck = Boolean(alert.acknowledged || alert.status === 'ACKNOWLEDGED');
  const severity = (alert.severity || 'INFO').toUpperCase();

  // Restrained POLARIS operational palette
  const getSeverityStyle = (sev) => {
    switch (sev) {
      case 'CRITICAL':
        return {
          color: '#c82a2a',
          bgBadge: 'rgba(200, 42, 42, 0.08)',
          borderLeft: '4px solid #c82a2a',
          borderTag: '1px solid rgba(200, 42, 42, 0.35)',
          tagLabel: 'CRITICAL ALARM'
        };
      case 'WARNING':
        return {
          color: '#d9821a',
          bgBadge: 'rgba(217, 130, 26, 0.08)',
          borderLeft: '4px solid #d9821a',
          borderTag: '1px solid rgba(217, 130, 26, 0.35)',
          tagLabel: 'WARNING'
        };
      case 'OFFLINE':
        return {
          color: '#727b87',
          bgBadge: 'rgba(114, 123, 135, 0.08)',
          borderLeft: '4px solid #727b87',
          borderTag: '1px solid rgba(114, 123, 135, 0.35)',
          tagLabel: 'OFFLINE'
        };
      case 'INFO':
      default:
        return {
          color: '#b65a1f',
          bgBadge: 'rgba(182, 90, 31, 0.08)',
          borderLeft: '4px solid #b65a1f',
          borderTag: '1px solid rgba(182, 90, 31, 0.35)',
          tagLabel: 'INFO'
        };
    }
  };

  const sevStyle = getSeverityStyle(severity);
  const sensorId = alert.sensor_id || alert.sensorId;
  const anomalyScore = typeof alert.anomaly_score === 'number'
    ? alert.anomaly_score
    : typeof alert.anomalyScore === 'number'
      ? alert.anomalyScore
      : null;

  return (
    <article
      className={`alert-card-row ${isAck ? 'acknowledged' : 'active'}`}
      style={{ borderLeft: isAck ? '4px solid #b8b0a2' : sevStyle.borderLeft }}
      aria-label={`Alert: ${alert.title}`}
    >
      <div className="alert-card-main">
        {/* Header strip: Severity Badge, Sensor ID, Zone, Station, Timestamp */}
        <div className="alert-meta-strip">
          <div className="alert-meta-left">
            <span
              className="alert-severity-pill"
              style={{
                color: isAck ? '#5d6672' : sevStyle.color,
                background: isAck ? 'rgba(0,0,0,0.04)' : sevStyle.bgBadge,
                border: isAck ? '1px solid var(--polaris-border)' : sevStyle.borderTag
              }}
            >
              <span
                className="severity-dot"
                style={{ background: isAck ? '#727b87' : sevStyle.color }}
              />
              {sevStyle.tagLabel}
            </span>

            {sensorId && (
              <span className="alert-sensor-tag">
                SENSOR // <strong style={{ color: 'var(--polaris-text-primary)' }}>{sensorId}</strong>
              </span>
            )}

            {alert.zone && (
              <span className="alert-zone-tag">
                ZONE: <strong>{alert.zone}</strong>
              </span>
            )}

            <span className="alert-station-tag">
              {alert.station_id || alert.station || 'MAITRI'}
            </span>
          </div>

          <div className="alert-meta-right">
            {anomalyScore !== null && (
              <span className="alert-anomaly-badge">
                ANOMALY SCORE: <strong>{anomalyScore.toFixed(2)}</strong>
              </span>
            )}
            <span className="alert-time-stamp">{alert.timestamp}</span>
          </div>
        </div>

        {/* Title & Message */}
        <div className="alert-content-block">
          <h2 className="alert-item-title">{alert.title}</h2>
          <p className="alert-item-message">{alert.message}</p>
        </div>

        {/* Action Controls Bar */}
        <div className="alert-actions-bar">
          <div className="alert-status-indication">
            {isAck ? (
              <span className="status-ack-tag">
                ✓ ACKNOWLEDGED {alert.acknowledgedAt ? `(${alert.acknowledgedAt})` : ''}
              </span>
            ) : (
              <span className="status-live-tag">
                ● ACTIVE INCIDENT
              </span>
            )}
          </div>

          <div className="alert-button-group">
            {/* Locate in Digital Twin */}
            {sensorId && (
              <button
                type="button"
                className="alert-action-btn locate-btn"
                onClick={() => onLocate && onLocate(alert)}
                title={`Open 3D Digital Twin and locate sensor ${sensorId}`}
              >
                ⌖ LOCATE IN DIGITAL TWIN
              </button>
            )}

            {/* Acknowledge Alert */}
            {!isAck && (
              <button
                type="button"
                className="alert-action-btn ack-btn"
                onClick={() => onAcknowledge && onAcknowledge(alert.id)}
                title="Acknowledge alert and audit in history"
              >
                ✓ ACKNOWLEDGE
              </button>
            )}
          </div>
        </div>
      </div>
    </article>
  );
};

export default AlertRow;
