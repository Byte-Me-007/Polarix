import React from 'react';

/**
 * AlertSummaryCards
 * Displays real-time operational summary metrics: CRITICAL, WARNING, OFFLINE, ACKNOWLEDGED.
 * Derives dynamic counts directly from the shared alert state.
 */
export const AlertSummaryCards = ({ alerts = [], activeFilter = 'ALL', onSelectFilter }) => {
  const criticalCount = alerts.filter((a) => !a.acknowledged && a.severity === 'CRITICAL').length;
  const warningCount = alerts.filter((a) => !a.acknowledged && a.severity === 'WARNING').length;
  const offlineCount = alerts.filter((a) => !a.acknowledged && a.severity === 'OFFLINE').length;
  const ackCount = alerts.filter((a) => a.acknowledged).length;

  const cards = [
    {
      key: 'CRITICAL',
      label: 'CRITICAL',
      count: criticalCount,
      color: '#c82a2a',
      bgLight: 'rgba(200, 42, 42, 0.06)',
      borderColor: 'rgba(200, 42, 42, 0.25)',
      description: 'Active severe alarm'
    },
    {
      key: 'WARNING',
      label: 'WARNING',
      count: warningCount,
      color: '#d9821a',
      bgLight: 'rgba(217, 130, 26, 0.06)',
      borderColor: 'rgba(217, 130, 26, 0.25)',
      description: 'Cautionary threshold'
    },
    {
      key: 'OFFLINE',
      label: 'OFFLINE',
      count: offlineCount,
      color: '#727b87',
      bgLight: 'rgba(114, 123, 135, 0.06)',
      borderColor: 'rgba(114, 123, 135, 0.25)',
      description: 'Dropout / no signal'
    },
    {
      key: 'ACKNOWLEDGED',
      label: 'ACKNOWLEDGED',
      count: ackCount,
      color: '#3f6e4a',
      bgLight: 'rgba(63, 110, 74, 0.06)',
      borderColor: 'rgba(63, 110, 74, 0.25)',
      description: 'Audited in history'
    }
  ];

  return (
    <div className="alert-summary-grid" role="region" aria-label="Alert Severity Summary">
      {cards.map((c) => {
        const isSelected = activeFilter === c.key;
        return (
          <button
            key={c.key}
            type="button"
            className={`alert-summary-card ${isSelected ? 'active' : ''}`}
            onClick={() => onSelectFilter && onSelectFilter(c.key)}
            style={{
              borderColor: isSelected ? c.color : undefined
            }}
          >
            <div className="summary-card-top">
              <span className="summary-card-indicator" style={{ background: c.color }} />
              <span className="summary-card-label">{c.label}</span>
            </div>

            <div className="summary-card-count" style={{ color: c.color }}>
              {String(c.count).padStart(2, '0')}
            </div>

            <div className="summary-card-desc">{c.description}</div>
          </button>
        );
      })}
    </div>
  );
};

export default AlertSummaryCards;
