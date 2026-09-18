import React from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * LogisticsAlertsCard
 * Synchronized list of logistics, supply, and storage alarms.
 * Includes deep link to central alerts console (/alerts).
 */
export const LogisticsAlertsCard = ({
  alerts = [],
  activeStation = 'MAITRI'
}) => {
  const navigate = useNavigate();

  // Filter alerts relevant to Logistics, Storage, Fuel, or Supplies
  const logisticsAlerts = alerts.filter((a) => {
    const type = (a.type || a.subsystem || '').toUpperCase();
    const zone = (a.zone || '').toUpperCase();
    const title = (a.title || '').toUpperCase();
    return (
      type === 'LOGISTICS' ||
      zone.includes('STORAGE') ||
      title.includes('FUEL') ||
      title.includes('DAY TANK') ||
      title.includes('SUPPLY') ||
      title.includes('BLIZZARD') ||
      title.includes('RESUPPLY')
    );
  });

  return (
    <section className="logistics-alerts-card" aria-label="Logistics System Alerts">
      <div className="card-header-row">
        <div>
          <h3 className="card-title">ACTIVE LOGISTICS & SUPPLY ALARMS</h3>
          <span className="card-subtitle">
            SYNCHRONIZED WITH EXPEDITION INCIDENT LOG ({logisticsAlerts.length})
          </span>
        </div>
        <button
          type="button"
          className="view-alerts-console-btn"
          onClick={() => navigate('/alerts')}
        >
          VIEW IN ALERTS CONSOLE →
        </button>
      </div>

      <div className="logistics-alerts-list">
        {logisticsAlerts.length === 0 ? (
          <div className="logistics-alerts-empty">
            ✓ No anomalous supply chain or storage incidents registered for {activeStation}.
          </div>
        ) : (
          logisticsAlerts.map((alert) => {
            const isCrit = alert.severity === 'CRITICAL';
            const isWarn = alert.severity === 'WARNING';
            const color = isCrit ? '#c82a2a' : isWarn ? '#d9821a' : '#757d85';

            return (
              <div
                key={alert.id}
                className="logistics-alert-item"
                style={{ borderLeftColor: color }}
              >
                <div className="l-alert-top">
                  <span
                    className="l-alert-sev"
                    style={{
                      color,
                      background: isCrit ? 'rgba(200,42,42,0.08)' : 'rgba(217,130,26,0.08)'
                    }}
                  >
                    ● {alert.severity}
                  </span>
                  <span className="l-alert-zone">{alert.zone || 'LOGISTICS'}</span>
                  <span className="l-alert-sensor">{alert.sensor_id || alert.sensorId || ''}</span>
                  <span className="l-alert-time">{alert.timestamp}</span>
                </div>

                <div className="l-alert-title">{alert.title}</div>
                <div className="l-alert-msg">{alert.message}</div>

                <div className="l-alert-actions">
                  <button
                    type="button"
                    className="view-alert-btn"
                    onClick={() => navigate('/alerts')}
                  >
                    VIEW IN ALERTS →
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
};

export default LogisticsAlertsCard;
