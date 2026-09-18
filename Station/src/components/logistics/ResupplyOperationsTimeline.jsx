import React from 'react';

/**
 * ResupplyOperationsTimeline
 * Chronological upcoming resupply shipments with cargo weights, transport modes,
 * ETAs, operational statuses, and interactive 'VIEW MANIFEST' button.
 */
export const ResupplyOperationsTimeline = ({
  missions = [],
  onOpenManifest
}) => {
  const getStatusBadge = (status) => {
    switch (status) {
      case 'IN TRANSIT':
        return { label: 'IN TRANSIT', cls: 'copper' };
      case 'APPROACHING':
        return { label: 'APPROACHING', cls: 'sage' };
      case 'LOADING':
        return { label: 'LOADING', cls: 'amber' };
      case 'DELAYED':
        return { label: 'DELAYED', cls: 'red' };
      case 'PLANNED':
        return { label: 'PLANNED', cls: 'muted' };
      default:
        return { label: status, cls: 'muted' };
    }
  };

  return (
    <section className="resupply-operations-card" aria-label="Resupply Operations Timeline">
      <div className="card-header-row">
        <div>
          <h3 className="card-title">RESUPPLY OPERATIONS & CARGO MISSIONS</h3>
          <span className="card-subtitle">
            CHRONOLOGICAL EXPEDITION TRANSPORT TIMELINE ({missions.length} SCHEDULED)
          </span>
        </div>
        <span className="card-tag">ANTARCTIC LOGISTICS CORRIDOR</span>
      </div>

      <div className="missions-timeline-list">
        {missions.map((m, idx) => {
          const badge = getStatusBadge(m.status);
          return (
            <div key={m.missionId || idx} className={`mission-card ${badge.cls}`}>
              <div className="mission-card-top">
                <div className="mission-id-wrap">
                  <span className="mission-id">{m.missionId}</span>
                  <span className="mission-transport-badge">{m.transport}</span>
                </div>
                <div className="mission-status-group">
                  <span className={`mission-status-pill ${badge.cls}`}>
                    ● {badge.label}
                  </span>
                  <span className="mission-eta-pill">ETA: <strong>{m.etaDays} DAYS</strong></span>
                </div>
              </div>

              <div className="mission-route-row">
                <span className="route-endpoint origin">ORIGIN: {m.origin}</span>
                <span className="route-arrow">➔</span>
                <span className="route-endpoint dest">DEST: {m.destination}</span>
              </div>

              <div className="mission-cargo-summary">
                <div className="cargo-text-wrap">
                  <span className="cargo-label">CARGO MANIFEST SUMMARY</span>
                  <p className="cargo-summary-text">{m.cargoSummary}</p>
                </div>
                <div className="cargo-weight-wrap">
                  <span className="cargo-label">PAYLOAD</span>
                  <span className="cargo-weight">{m.weightTons.toFixed(1)} t</span>
                </div>
              </div>

              <div className="mission-actions-bar">
                <span className="mission-confidence">Confidence: {m.confidence}</span>
                <button
                  type="button"
                  className="view-manifest-btn"
                  onClick={() => onOpenManifest && onOpenManifest(m)}
                >
                  📋 VIEW CARGO MANIFEST →
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default ResupplyOperationsTimeline;
