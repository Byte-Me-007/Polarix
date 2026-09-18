import React from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * EnergyAlertsList
 * Compact list of active energy-related alerts with 1-click navigation
 * to the Alerts management page and deep link to 3D Digital Twin.
 */
export const EnergyAlertsList = ({
  alerts = [],
  activeStation = 'MAITRI'
}) => {
  const navigate = useNavigate();

  // Filter alerts relevant to Energy, Generator, Battery, or Logistics fuel
  const energyAlerts = alerts.filter((a) => {
    const type = (a.type || a.subsystem || '').toUpperCase();
    const zone = (a.zone || '').toUpperCase();
    const title = (a.title || '').toUpperCase();
    return (
      type === 'ENERGY' ||
      type === 'BATTERY' ||
      zone.includes('ENERGY') ||
      zone.includes('GENERATOR') ||
      title.includes('GENERATOR') ||
      title.includes('POWER') ||
      title.includes('BATTERY') ||
      title.includes('FUEL')
    );
  });

  const handleViewAllAlerts = () => {
    navigate('/alerts');
  };

  const handleLocateInTwin = (alert) => {
    navigate('/digital-twin', {
      state: { locateSensorId: alert.sensor_id || alert.sensorId || 'ENG-MTR-002' }
    });
  };

  return (
    <section className="energy-alerts-card" aria-label="Energy System Alerts">
      <div className="card-header-row">
        <div>
          <h3 className="card-title">ACTIVE ENERGY ALARMS & ADVISORIES</h3>
          <span className="card-subtitle">
            SYNCHRONIZED WITH CENTRAL INCIDENT LOG ({energyAlerts.length})
          </span>
        </div>
        <button
          type="button"
          className="view-all-alerts-btn"
          onClick={handleViewAllAlerts}
        >
          VIEW IN ALERTS CONSOLE →
        </button>
      </div>

      <div className="energy-alerts-list">
        {energyAlerts.length === 0 ? (
          <div className="energy-alerts-empty">
            ✓ No anomalous energy or microgrid alerts registered for {activeStation}.
          </div>
        ) : (
          energyAlerts.map((alert) => {
            const isCrit = alert.severity === 'CRITICAL';
            const color = isCrit ? '#c82a2a' : '#d9821a';

            return (
              <div
                key={alert.id}
                className="energy-alert-item"
                style={{ borderLeftColor: color }}
              >
                <div className="e-alert-top">
                  <span
                    className="e-alert-sev"
                    style={{ color, background: isCrit ? 'rgba(200,42,42,0.08)' : 'rgba(217,130,26,0.08)' }}
                  >
                    ● {alert.severity}
                  </span>
                  <span className="e-alert-zone">{alert.zone || 'ENERGY'}</span>
                  <span className="e-alert-sensor">{alert.sensor_id || alert.sensorId || ''}</span>
                  <span className="e-alert-time">{alert.timestamp}</span>
                </div>

                <div className="e-alert-title">{alert.title}</div>
                <div className="e-alert-msg">{alert.message}</div>

                <div className="e-alert-actions">
                  <button
                    type="button"
                    className="e-locate-btn"
                    onClick={() => handleLocateInTwin(alert)}
                  >
                    ⌖ VIEW IN DIGITAL TWIN
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

export default EnergyAlertsList;
