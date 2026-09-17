import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useStationTelemetry } from '../hooks/useStationTelemetry';

export const AlertSummary = () => {
  const { alerts } = useStationTelemetry();
  const navigate = useNavigate();

  const handleEventClick = (eventId) => {
    navigate('/alerts', { state: { selectedAlertId: eventId } });
  };

  const getMarkerClass = (sev) => {
    switch (sev) {
      case 'CRITICAL': return 'critical';
      case 'WARNING': return 'warning';
      case 'INFO':
      default: return 'info';
    }
  };

  return (
    <section className="events-timeline-section" id="active-events-panel">
      <div className="events-header">
        <div className="events-title">
          <span>ACTIVE EVENTS</span>
          <span className="events-count-stamp">
            {String(alerts.length).padStart(2, '0')} LOGGED
          </span>
        </div>

        <button
          type="button"
          onClick={() => navigate('/alerts')}
          style={{
            background: 'none',
            border: 'none',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.6875rem',
            fontWeight: 600,
            color: 'var(--polaris-copper)',
            cursor: 'pointer',
            padding: 0
          }}
        >
          VIEW ALL ALARMS →
        </button>
      </div>

      {/* Vertical Operational Timeline */}
      <div className="timeline-list">
        {alerts.length === 0 ? (
          <div style={{ padding: '1rem 0', color: 'var(--polaris-text-muted)', fontSize: '0.8125rem' }}>
            ● No anomalous events registered on active station bus.
          </div>
        ) : (
          alerts.map((alert) => {
            const markerCls = getMarkerClass(alert.severity);
            return (
              <div
                key={alert.id}
                className="timeline-event-item"
                onClick={() => handleEventClick(alert.id)}
                title="Click to view diagnostic event log"
              >
                <div className={`timeline-marker ${markerCls}`} />

                <div className="timeline-meta-row">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                    <span className={`event-severity-tag ${markerCls}`}>
                      ● {alert.severity}
                    </span>
                    <span>//</span>
                    <span style={{ color: 'var(--polaris-text-secondary)', fontWeight: 600 }}>
                      {alert.subsystem || 'TELEMETRY'}
                    </span>
                  </div>
                  <span>{alert.timestamp}</span>
                </div>

                <div className="timeline-event-title">{alert.title}</div>
                <div className="timeline-event-message">{alert.message}</div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
};

export default AlertSummary;
