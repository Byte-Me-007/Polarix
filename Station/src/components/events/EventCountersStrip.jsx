import React from 'react';

/**
 * EventCountersStrip
 * Operational event KPI counters derived live from the current event stream.
 */
export const EventCountersStrip = ({
  totalCount = 0,
  criticalCount = 0,
  warningCount = 0,
  infoCount = 0,
  lastEventTime = 'Just now'
}) => {
  const metrics = [
    {
      label: 'TOTAL EVENTS',
      value: totalCount < 10 ? `0${totalCount}` : `${totalCount}`,
      sub: 'Recorded station actions',
      color: 'var(--polaris-text-primary)'
    },
    {
      label: 'CRITICAL EVENTS',
      value: criticalCount < 10 ? `0${criticalCount}` : `${criticalCount}`,
      sub: criticalCount > 0 ? 'Requires priority attention' : 'No critical incidents',
      color: criticalCount > 0 ? '#c82a2a' : '#3f6e4a'
    },
    {
      label: 'WARNINGS',
      value: warningCount < 10 ? `0${warningCount}` : `${warningCount}`,
      sub: 'Threshold advisories',
      color: warningCount > 0 ? '#d9821a' : 'var(--polaris-text-primary)'
    },
    {
      label: 'INFORMATIONAL / NORMAL',
      value: infoCount < 10 ? `0${infoCount}` : `${infoCount}`,
      sub: 'Telemetry & mission logs',
      color: 'var(--polaris-text-secondary)'
    },
    {
      label: 'LAST EVENT RECORDED',
      value: lastEventTime || 'TIME UNAVAILABLE',
      sub: 'Station telemetry heartbeat',
      color: 'var(--polaris-copper)'
    }
  ];

  return (
    <div className="event-counters-strip" role="region" aria-label="Event Counters">
      {metrics.map((m, idx) => (
        <div key={idx} className="event-counter-card">
          <span className="event-counter-label">{m.label}</span>
          <span className="event-counter-val" style={{ color: m.color }}>
            {m.value}
          </span>
          <span className="event-counter-sub">{m.sub}</span>
        </div>
      ))}
    </div>
  );
};

export default EventCountersStrip;
