import React from 'react';

/**
 * StorageUtilizationCard
 * Breakdown of station storage facilities (Main, Fuel, Cold Storage, Scientific, Emergency)
 * with compact utilization bars and 'VIEW STORAGE IN DIGITAL TWIN' cross-navigation.
 */
export const StorageUtilizationCard = ({
  facilities = [],
  onLocateInTwin
}) => {
  return (
    <section className="storage-utilization-card" aria-label="Storage Facility Utilization">
      <div className="card-header-row">
        <div>
          <h3 className="card-title">STORAGE FACILITY UTILIZATION</h3>
          <span className="card-subtitle">
            STATION LOGISTICS BAYS & CRYOGENIC HOLD CAPACITIES
          </span>
        </div>
        {onLocateInTwin && (
          <button
            type="button"
            className="storage-twin-btn"
            onClick={() => onLocateInTwin('LOG-MTR-004')}
          >
            ⌖ VIEW STORAGE IN DIGITAL TWIN
          </button>
        )}
      </div>

      <div className="storage-facilities-grid">
        {facilities.map((fac, idx) => {
          const avail = Math.max(0, fac.capacityTons - fac.usedTons);
          const isHigh = fac.utilizationPct >= 80;
          const barColor = isHigh ? '#d9821a' : '#3f6e4a';

          return (
            <div key={idx} className="storage-facility-box">
              <div className="fac-header">
                <span className="fac-name">{fac.name}</span>
                <span className="fac-pct" style={{ color: barColor }}>
                  {fac.utilizationPct}% USED
                </span>
              </div>

              {/* Progress Bar */}
              <div className="fac-progress-track">
                <div
                  className="fac-progress-fill"
                  style={{
                    width: `${fac.utilizationPct}%`,
                    background: barColor
                  }}
                />
              </div>

              <div className="fac-metrics-row">
                <div className="fac-sub-metric">
                  <span className="sub-m-label">USED</span>
                  <span className="sub-m-val">{fac.usedTons.toFixed(1)} {fac.unit}</span>
                </div>
                <div className="fac-sub-metric">
                  <span className="sub-m-label">CAPACITY</span>
                  <span className="sub-m-val">{fac.capacityTons.toFixed(1)} {fac.unit}</span>
                </div>
                <div className="fac-sub-metric">
                  <span className="sub-m-label">AVAILABLE</span>
                  <span className="sub-m-val">{avail.toFixed(1)} {fac.unit}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default StorageUtilizationCard;
