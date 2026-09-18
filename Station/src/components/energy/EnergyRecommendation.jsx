import React, { useState } from 'react';

/**
 * EnergyRecommendation
 * Explainable rule recommendation panel for operators.
 * Displays operational triggers, conditions, actionable directives,
 * and expandable telemetry audit parameters to ensure full transparency.
 */
export const EnergyRecommendation = ({
  recommendation,
  batterySoc = 78,
  renewableShare = 72,
  loadKw = 84.3,
  remainingHours = '38.5 hrs'
}) => {
  const [showExplanation, setShowExplanation] = useState(true);

  if (!recommendation) {
    return (
      <section className="recommendation-card nominal" aria-label="Energy Recommendation">
        <div className="card-header-row">
          <div>
            <h3 className="card-title">ENERGY OPERATIONS RECOMMENDATION</h3>
            <span className="card-subtitle">EXPLAINABLE RULE-BASED DISPATCH ADVISORY</span>
          </div>
          <span className="rec-badge sage">● NOMINAL</span>
        </div>
        <div className="rec-empty-state">
          NO ACTIVE RECOMMENDATION — Microgrid bus frequency, battery SOC, and renewable contribution are within nominal operating envelopes.
        </div>
      </section>
    );
  }

  const {
    title = 'POWER CONSERVATION PROTOCOL',
    severity = 'WARNING',
    trigger = 'Battery SOC decreasing under high station demand',
    condition = 'Renewable generation below facility baseline load',
    action = 'Engage non-essential load shedding; throttle scientific laboratory heaters',
    metrics = []
  } = recommendation;

  const isCritical = severity === 'CRITICAL';
  const color = isCritical ? '#c82a2a' : severity === 'WARNING' ? '#d9821a' : '#3f6e4a';

  return (
    <section
      className="recommendation-card"
      style={{ borderLeft: `4px solid ${color}` }}
      aria-label="Energy Operations Recommendation"
    >
      <div className="card-header-row">
        <div>
          <h3 className="card-title">ENERGY OPERATIONS RECOMMENDATION</h3>
          <span className="card-subtitle">MISSION-CONTROL RULE ENGINE ADVISORY</span>
        </div>
        <span
          className="rec-badge"
          style={{ color, borderColor: color, background: isCritical ? 'rgba(200,42,42,0.08)' : 'rgba(217,130,26,0.08)' }}
        >
          ● {severity} ADVISORY
        </span>
      </div>

      <div className="rec-title-block">
        <h4 className="rec-headline">{title}</h4>
      </div>

      {/* Structured Operational Directive (Trigger, Condition, Action) */}
      <div className="rec-structured-grid">
        <div className="rec-box">
          <span className="rec-label">TRIGGER</span>
          <p className="rec-text">{trigger}</p>
        </div>

        <div className="rec-box">
          <span className="rec-label">CONDITION</span>
          <p className="rec-text">{condition}</p>
        </div>

        <div className="rec-box action-box">
          <span className="rec-label action-label">DIRECTIVE / ACTION</span>
          <p className="rec-text action-text">{action}</p>
        </div>
      </div>

      {/* Expandable Explainability Section: WHY THIS WAS TRIGGERED */}
      <div className="why-triggered-wrap">
        <button
          type="button"
          className="why-toggle-btn"
          onClick={() => setShowExplanation(!showExplanation)}
        >
          <span>{showExplanation ? '▼' : '►'} WHY THIS WAS TRIGGERED (TELEMETRY AUDIT)</span>
          <span className="why-toggle-sub">Operator transparency log</span>
        </button>

        {showExplanation && (
          <div className="why-content-panel">
            <ul className="why-metrics-list">
              <li>
                <span>Battery State of Charge (SOC):</span>
                <strong>{batterySoc}%</strong>
              </li>
              <li>
                <span>Renewable Energy Contribution:</span>
                <strong>{renewableShare}%</strong>
              </li>
              <li>
                <span>Total Active Station Load:</span>
                <strong>{loadKw.toFixed(1)} kW</strong>
              </li>
              <li>
                <span>Estimated Battery Buffer Runtime:</span>
                <strong>{remainingHours}</strong>
              </li>
              {metrics.map((m, idx) => (
                <li key={idx}>
                  <span>{m.label}:</span>
                  <strong>{m.val}</strong>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
};

export default EnergyRecommendation;
