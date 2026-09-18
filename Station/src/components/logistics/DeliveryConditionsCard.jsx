import React from 'react';

/**
 * DeliveryConditionsCard
 * Route and delivery operational conditions, weather impact, and ETA confidence.
 * Dynamically reacts to blizzard storm conditions in demo mode.
 */
export const DeliveryConditionsCard = ({
  conditions,
  scenario = 'NORMAL'
}) => {
  if (!conditions) {
    return (
      <section className="delivery-conditions-card" aria-label="Delivery Conditions">
        <div className="card-header-row">
          <div>
            <h3 className="card-title">DELIVERY CONDITIONS & ROUTE RISK</h3>
            <span className="card-subtitle">POLAR CORRIDOR WEATHER TELEMETRY</span>
          </div>
        </div>
        <div className="conditions-empty-note">
          NO LIVE ROUTE RISK DATA AVAILABLE
        </div>
      </section>
    );
  }

  const isStorm = scenario === 'STORM';

  const routeStatus = isStorm
    ? 'BLIZZARD RESTRICTION — AIR CORRIDOR GROUNDED'
    : conditions.routeStatus;

  const deliveryRisk = isStorm
    ? 'HIGH (BLIZZARD)'
    : conditions.deliveryRisk;

  const weatherImpact = isStorm
    ? 'Sustained blizzard gusts 118 km/h. Optical visibility < 50m. Runway unserviced.'
    : conditions.weatherImpact;

  const etaConfidence = isStorm
    ? 'FLIGHT DELAYED (+5 DAYS ESTIMATED)'
    : conditions.etaConfidence;

  const riskColor = isStorm ? '#c82a2a' : deliveryRisk === 'LOW' ? '#3f6e4a' : '#d9821a';

  return (
    <section className="delivery-conditions-card" aria-label="Delivery Conditions">
      <div className="card-header-row">
        <div>
          <h3 className="card-title">DELIVERY CONDITIONS & ROUTE RISK</h3>
          <span className="card-subtitle">
            ANTARCTIC TRANSIT AIR & SEA CORRIDOR STATUS
          </span>
        </div>
        <span
          className="risk-badge"
          style={{
            color: riskColor,
            borderColor: riskColor,
            background: isStorm ? 'rgba(200,42,42,0.08)' : 'rgba(63,110,74,0.08)'
          }}
        >
          ● {deliveryRisk}
        </span>
      </div>

      <div className="conditions-grid">
        <div className="condition-item">
          <span className="cond-label">CURRENT ROUTE STATUS</span>
          <span className="cond-val" style={{ color: isStorm ? '#c82a2a' : 'var(--polaris-text-primary)' }}>
            {routeStatus}
          </span>
        </div>

        <div className="condition-item">
          <span className="cond-label">ETA CONFIDENCE</span>
          <span className="cond-val" style={{ color: isStorm ? '#d9821a' : 'var(--polaris-text-primary)' }}>
            {etaConfidence}
          </span>
        </div>

        <div className="condition-item full-width">
          <span className="cond-label">METEOROLOGICAL IMPACT</span>
          <p className="cond-text">{weatherImpact}</p>
        </div>
      </div>
    </section>
  );
};

export default DeliveryConditionsCard;
