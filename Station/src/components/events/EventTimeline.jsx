import React from 'react';

/**
 * EventTimeline
 * Chronological vertical timeline displaying events grouped by TODAY vs PREVIOUS RECORDS.
 * Connected line nodes communicate temporal sequence and operational causality.
 */
export const EventTimeline = ({
  events = [],
  selectedEventId,
  onSelectEvent,
  onViewSensor,
  onViewAlert,
  onViewEnergy,
  onViewLogistics
}) => {
  if (events.length === 0) {
    return (
      <div className="timeline-empty-card">
        <div className="empty-icon">📋</div>
        <div className="empty-title">NO EVENTS FOUND MATCHING CRITERIA</div>
        <p className="empty-desc">
          Try expanding your search query, resetting severity filters, or broadening the time range window.
        </p>
      </div>
    );
  }

  // Split events into Today vs Previous
  const todayEvents = events.filter((e) => e.isToday);
  const historyEvents = events.filter((e) => !e.isToday);

  const renderEventItem = (event) => {
    const isSelected = selectedEventId === event.id;
    const isCrit = event.severity === 'CRITICAL';
    const isWarn = event.severity === 'WARNING';
    const isNorm = event.severity === 'NORMAL';
    const nodeColor = isCrit ? '#c82a2a' : isWarn ? '#d9821a' : isNorm ? '#3f6e4a' : '#757d85';
    const sevClass = event.severity ? event.severity.toLowerCase() : 'info';

    const hasRelated = event.related_event_ids && event.related_event_ids.length > 0;

    return (
      <div
        key={event.id}
        className={`timeline-entry ${isSelected ? 'selected' : ''} ${sevClass}`}
        onClick={() => onSelectEvent && onSelectEvent(event)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onSelectEvent && onSelectEvent(event);
          }
        }}
        aria-label={`Event ${event.title}`}
      >
        {/* Timeline Node Point on Connected Line */}
        <div className="timeline-node-marker">
          <span
            className="node-dot"
            style={{
              background: nodeColor,
              boxShadow: isCrit ? '0 0 8px rgba(200,42,42,0.4)' : undefined
            }}
          />
          <span className="timeline-connector-line" />
        </div>

        {/* Event Content Box */}
        <div className="timeline-content-card">
          <div className="event-meta-top">
            <span className="event-time-stamp">{event.timestamp || 'TIME UNAVAILABLE'}</span>
            <span className="event-category-tag">{event.category || 'SYSTEM'}</span>
            <span
              className={`event-severity-pill ${sevClass}`}
              style={{
                color: nodeColor,
                borderColor: nodeColor,
                background: isCrit ? 'rgba(200,42,42,0.08)' : isWarn ? 'rgba(217,130,26,0.08)' : isNorm ? 'rgba(63,110,74,0.08)' : 'rgba(117,125,133,0.08)'
              }}
            >
              ● {event.severity || 'INFO'}
            </span>

            {hasRelated && (
              <span className="correlation-indicator" title="Connected sequence cascade">
                🔗 CASCADE ({event.related_event_ids.length} RELATED)
              </span>
            )}

            <span className="event-time-ago">{event.timeAgo || ''}</span>
          </div>

          <h4 className="event-card-title">{event.title}</h4>
          <p className="event-card-desc">{event.description}</p>

          <div className="event-footer-bar">
            <div className="event-location-info">
              <span className="info-item">
                <strong>ZONE:</strong> {event.zone || 'STATION UNKNOWN'}
              </span>
              <span className="info-separator">•</span>
              <span className="info-item">
                <strong>SOURCE:</strong> {event.source || 'SOURCE UNKNOWN'}
              </span>
              {event.sensor_id && (
                <>
                  <span className="info-separator">•</span>
                  <span className="info-item">
                    <strong>SENSOR:</strong> {event.sensor_id}
                  </span>
                </>
              )}
            </div>

            {/* Quick Context Actions */}
            <div className="event-quick-actions" onClick={(e) => e.stopPropagation()}>
              {event.sensor_id && onViewSensor && (
                <button
                  type="button"
                  className="quick-action-btn twin-btn"
                  onClick={() => onViewSensor(event.sensor_id)}
                  title="View sensor in 3D Digital Twin"
                >
                  ⌖ VIEW SENSOR
                </button>
              )}
              {event.alert_id && onViewAlert && (
                <button
                  type="button"
                  className="quick-action-btn alert-btn"
                  onClick={() => onViewAlert(event.alert_id)}
                  title="View alert details"
                >
                  ⚠ VIEW ALERT
                </button>
              )}
              {event.category === 'ENERGY' && onViewEnergy && (
                <button
                  type="button"
                  className="quick-action-btn energy-btn"
                  onClick={() => onViewEnergy()}
                  title="Open Energy Console"
                >
                  ⚡ VIEW ENERGY
                </button>
              )}
              {(event.category === 'LOGISTICS' || event.category === 'MISSION') && onViewLogistics && (
                <button
                  type="button"
                  className="quick-action-btn logistics-btn"
                  onClick={() => onViewLogistics()}
                  title="Open Logistics Console"
                >
                  📦 VIEW LOGISTICS
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="event-timeline-container" role="region" aria-label="Chronological Mission Timeline">
      {/* Today's Section */}
      {todayEvents.length > 0 && (
        <div className="timeline-date-group">
          <div className="date-group-divider">
            <span className="divider-line" />
            <span className="date-group-badge">
              TODAY // 18 SEP 2026 ({todayEvents.length} EVENTS)
            </span>
            <span className="divider-line" />
          </div>

          <div className="timeline-entries-list">
            {todayEvents.map(renderEventItem)}
          </div>
        </div>
      )}

      {/* History Section */}
      {historyEvents.length > 0 && (
        <div className="timeline-date-group">
          <div className="date-group-divider">
            <span className="divider-line" />
            <span className="date-group-badge history">
              PREVIOUS ACTIVITY // 17 SEP 2026 ({historyEvents.length} EVENTS)
            </span>
            <span className="divider-line" />
          </div>

          <div className="timeline-entries-list">
            {historyEvents.map(renderEventItem)}
          </div>
        </div>
      )}
    </div>
  );
};

export default EventTimeline;
