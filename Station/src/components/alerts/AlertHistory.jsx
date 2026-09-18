import React from 'react';

/**
 * AlertHistory
 * Compact audit table showing recently acknowledged or resolved operational incidents.
 * Columns: TIME, SEVERITY, EVENT, SENSOR, ZONE, STATUS
 */
export const AlertHistory = ({ historyAlerts = [], onLocate }) => {
  const getSeverityBadge = (sev) => {
    switch (sev) {
      case 'CRITICAL':
        return <span className="history-sev-tag critical">CRITICAL</span>;
      case 'WARNING':
        return <span className="history-sev-tag warning">WARNING</span>;
      case 'OFFLINE':
        return <span className="history-sev-tag offline">OFFLINE</span>;
      case 'INFO':
      default:
        return <span className="history-sev-tag info">INFO</span>;
    }
  };

  return (
    <section className="alert-history-section" aria-label="Alert History & Incident Audit">
      <div className="alert-history-header">
        <div className="history-title-block">
          <h3 className="history-title">ALERT HISTORY</h3>
          <span className="history-subtitle">
            AUDITED & ACKNOWLEDGED INCIDENTS ({historyAlerts.length})
          </span>
        </div>
      </div>

      <div className="history-table-wrapper">
        <table className="history-table">
          <thead>
            <tr>
              <th scope="col" style={{ width: '120px' }}>TIME</th>
              <th scope="col" style={{ width: '110px' }}>SEVERITY</th>
              <th scope="col">EVENT</th>
              <th scope="col" style={{ width: '140px' }}>SENSOR</th>
              <th scope="col" style={{ width: '150px' }}>ZONE</th>
              <th scope="col" style={{ width: '140px' }}>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {historyAlerts.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--polaris-text-muted)' }}>
                  No historical incidents recorded.
                </td>
              </tr>
            ) : (
              historyAlerts.map((alert) => {
                const sensorId = alert.sensor_id || alert.sensorId;
                return (
                  <tr key={`hist-${alert.id}`}>
                    <td className="mono-col">{alert.timestamp}</td>
                    <td>{getSeverityBadge(alert.severity)}</td>
                    <td>
                      <div className="history-event-title">{alert.title}</div>
                      <div className="history-event-msg">{alert.message}</div>
                    </td>
                    <td className="mono-col">
                      {sensorId ? (
                        <button
                          type="button"
                          className="history-sensor-link"
                          onClick={() => onLocate && onLocate(alert)}
                          title={`Locate sensor ${sensorId} in 3D Digital Twin`}
                        >
                          ⌖ {sensorId}
                        </button>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>
                      <span className="history-zone-badge">{alert.zone || 'STATION'}</span>
                    </td>
                    <td>
                      <span className="history-status-tag">
                        ✓ {alert.status || 'ACKNOWLEDGED'}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default AlertHistory;
