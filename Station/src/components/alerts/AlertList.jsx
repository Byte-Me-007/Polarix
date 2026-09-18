import React from 'react';
import { AlertRow } from './AlertRow';

/**
 * AlertList
 * Renders the primary list of active / filtered alerts.
 */
export const AlertList = ({ alerts = [], onAcknowledge, onLocate }) => {
  if (alerts.length === 0) {
    return (
      <div className="alert-empty-state" role="status">
        <div className="empty-state-icon">✓</div>
        <div className="empty-state-title">ALL SYSTEMS OPERATING NOMINALLY</div>
        <div className="empty-state-desc">
          No anomalous telemetry or active alarm conditions match the current filter criteria.
        </div>
      </div>
    );
  }

  return (
    <div className="alert-list-container" role="feed" aria-label="Active Operational Alerts">
      {alerts.map((alert) => (
        <AlertRow
          key={alert.id}
          alert={alert}
          onAcknowledge={onAcknowledge}
          onLocate={onLocate}
        />
      ))}
    </div>
  );
};

export default AlertList;
