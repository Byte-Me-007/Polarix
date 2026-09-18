import React from 'react';

/**
 * EventDetailDrawer
 * Expandable operational audit panel for an inspected event.
 * Displays physical telemetry thresholds, rule engine triggers & outcomes,
 * correlated causal cascade events, and module navigation actions.
 */
export const EventDetailDrawer = ({
  event,
  allEvents = [],
  onClose,
  onSelectEvent,
  onViewSensor,
  onViewAlert,
  onViewEnergy,
  onViewLogistics
}) => {
  if (!event) {
    return (
      <aside className="event-detail-drawer empty" aria-label="Event Details">
        <div className="drawer-placeholder">
          <div className="placeholder-icon">ℹ</div>
          <h4 className="placeholder-title">NO EVENT SELECTED</h4>
          <p className="placeholder-desc">
            Click any entry on the chronological timeline to inspect sensor parameters, rule triggers, and causal relationships.
          </p>
        </div>
      </aside>
    );
  }

  const isCrit = event.severity === 'CRITICAL';
  const isWarn = event.severity === 'WARNING';
  const sevColor = isCrit ? '#c82a2a' : isWarn ? '#d9821a' : '#3f6e4a';

  // Find related events if available
  const relatedEvents = (event.related_event_ids || [])
    .map((id) => allEvents.find((e) => e.id === id))
    .filter(Boolean);

  return (
    <aside className="event-detail-drawer" aria-label={`Details for event ${event.id}`}>
      {/* Header */}
      <div className="drawer-header" style={{ borderLeftColor: sevColor }}>
        <div>
          <div className="drawer-id-row">
            <span className="drawer-event-id">{event.id}</span>
            <span
              className="drawer-sev-badge"
              style={{
                color: sevColor,
                borderColor: sevColor,
                background: isCrit ? 'rgba(200,42,42,0.08)' : isWarn ? 'rgba(217,130,26,0.08)' : 'rgba(63,110,74,0.08)'
              }}
            >
              ● {event.severity}
            </span>
          </div>
          <h3 className="drawer-event-title">{event.title}</h3>
          <span className="drawer-event-time">
            Recorded: {event.timestamp || 'TIME UNAVAILABLE'} ({event.date})
          </span>
        </div>

        <button
          type="button"
          className="drawer-close-btn"
          onClick={onClose}
          aria-label="Close event details"
        >
          ✕
        </button>
      </div>

      <div className="drawer-body">
        {/* Core Metadata Grid */}
        <div className="drawer-section">
          <span className="drawer-section-label">OPERATIONAL CONTEXT</span>
          <div className="drawer-meta-grid">
            <div className="d-meta-item">
              <span className="d-label">STATION</span>
              <span className="d-val">{event.station_id || 'STATION UNKNOWN'}</span>
            </div>
            <div className="d-meta-item">
              <span className="d-label">ZONE</span>
              <span className="d-val">{event.zone || 'ZONE UNKNOWN'}</span>
            </div>
            <div className="d-meta-item">
              <span className="d-label">CATEGORY</span>
              <span className="d-val">{event.category || 'SYSTEM'}</span>
            </div>
            <div className="d-meta-item">
              <span className="d-label">SOURCE</span>
              <span className="d-val">{event.source || 'SOURCE UNKNOWN'}</span>
            </div>
            <div className="d-meta-item">
              <span className="d-label">STATUS</span>
              <span className="d-val">{event.status || 'LOGGED'}</span>
            </div>
          </div>
        </div>

        {/* Narrative Description */}
        <div className="drawer-section">
          <span className="drawer-section-label">INCIDENT / EVENT DESCRIPTION</span>
          <p className="drawer-description-text">{event.description}</p>
        </div>

        {/* Live Physical Telemetry & Thresholds (If Sensor Involved) */}
        {(event.sensor_id || event.current_value) && (
          <div className="drawer-section">
            <span className="drawer-section-label">SENSOR & TELEMETRY AUDIT</span>
            <div className="drawer-sensor-grid">
              <div className="s-audit-item">
                <span className="s-audit-label">SENSOR ID</span>
                <span className="s-audit-val mono">{event.sensor_id || 'N/A'}</span>
              </div>
              <div className="s-audit-item">
                <span className="s-audit-label">RECORDED VALUE</span>
                <span className="s-audit-val mono" style={{ color: sevColor, fontWeight: 700 }}>
                  {event.current_value || 'NOMINAL'}
                </span>
              </div>
              <div className="s-audit-item">
                <span className="s-audit-label">SAFETY THRESHOLD</span>
                <span className="s-audit-val mono">{event.threshold || 'N/A'}</span>
              </div>
              <div className="s-audit-item">
                <span className="s-audit-label">ANOMALY SCORE</span>
                <span className="s-audit-val mono">
                  {typeof event.anomaly_score === 'number'
                    ? (event.anomaly_score * 100).toFixed(0) + '%'
                    : 'N/A'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Rule Engine Audit (If Rule Triggered) */}
        {event.rule_triggered && (
          <div className="drawer-section">
            <span className="drawer-section-label">RULE ENGINE DISPATCH LOG</span>
            <div className="rule-audit-card">
              <div className="rule-row">
                <span className="rule-label">RULE TRIGGERED:</span>
                <span className="rule-val mono">{event.rule_triggered}</span>
              </div>
              <div className="rule-row">
                <span className="rule-label">RULE OUTCOME:</span>
                <span className="rule-val mono" style={{ color: 'var(--polaris-copper)' }}>
                  {event.rule_outcome}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Correlated Event Sequence Cascade */}
        {relatedEvents.length > 0 && (
          <div className="drawer-section">
            <span className="drawer-section-label">CORRELATED EVENT CASCADE ({relatedEvents.length})</span>
            <div className="related-events-stack">
              {relatedEvents.map((rel) => (
                <div
                  key={rel.id}
                  className="related-event-chip"
                  onClick={() => onSelectEvent && onSelectEvent(rel)}
                  role="button"
                  tabIndex={0}
                >
                  <span className="rel-time">{rel.timestamp}</span>
                  <span className="rel-title">{rel.title}</span>
                  <span className="rel-arrow">➔</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons Bar */}
        <div className="drawer-actions-section">
          <span className="drawer-section-label">OPERATIONAL ACTIONS</span>
          <div className="drawer-action-buttons">
            {event.sensor_id && onViewSensor && (
              <button
                type="button"
                className="drawer-action-btn twin-btn"
                onClick={() => onViewSensor(event.sensor_id)}
              >
                ⌖ LOCATE IN DIGITAL TWIN
              </button>
            )}
            {event.alert_id && onViewAlert && (
              <button
                type="button"
                className="drawer-action-btn alert-btn"
                onClick={() => onViewAlert(event.alert_id)}
              >
                ⚠ VIEW IN ALERTS CONSOLE
              </button>
            )}
            {event.category === 'ENERGY' && onViewEnergy && (
              <button
                type="button"
                className="drawer-action-btn energy-btn"
                onClick={() => onViewEnergy()}
              >
                ⚡ VIEW IN ENERGY MANAGEMENT
              </button>
            )}
            {(event.category === 'LOGISTICS' || event.category === 'MISSION') && onViewLogistics && (
              <button
                type="button"
                className="drawer-action-btn logistics-btn"
                onClick={() => onViewLogistics()}
              >
                📦 VIEW IN LOGISTICS & SUPPLY
              </button>
            )}
          </div>
        </div>
      </div>
    </aside>
  );
};

export default EventDetailDrawer;
