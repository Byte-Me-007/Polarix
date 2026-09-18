import React from 'react';

/**
 * ResupplyCoverageCard
 * Answers the central operational question:
 * WILL SUPPLIES LAST UNTIL THE NEXT RESUPPLY ARRIVES?
 *
 * Compares projected depletion days of critical categories against next resupply ETA.
 * Status:
 * - COVERED: buffer > 7 days after ETA
 * - WATCH: buffer between 0 and 7 days
 * - RESUPPLY RISK: supply expected to deplete BEFORE next resupply arrives!
 */
export const ResupplyCoverageCard = ({
  nextResupplyEta = 14,
  missionId = 'RESUPPLY-07',
  transport = 'LC-130 HERCULES AIRCRAFT',
  inventory = []
}) => {
  // Aggregate key supply categories
  const categoriesToCheck = [
    { key: 'FOOD', label: 'FOOD RATIONS' },
    { key: 'MEDICAL', label: 'MEDICAL OXYGEN / PHARMA' },
    { key: 'FUEL', label: 'POLAR DIESEL (SAB-55)' },
    { key: 'SPARE PARTS', label: 'CRITICAL SPARES (DG FILTERS)' }
  ];

  const coverageAnalysis = categoriesToCheck.map((cat) => {
    const items = inventory.filter((i) => i.category === cat.key);
    // Find minimum remaining days in this category
    const minDays = items.length > 0
      ? Math.min(...items.map((i) => i.remainingDays))
      : 999;

    const bufferDays = minDays - nextResupplyEta;

    let status = 'COVERED';
    let statusText = 'SAFE BUFFER';
    let color = '#3f6e4a';
    let badgeClass = 'sage';

    if (bufferDays < 0) {
      status = 'RESUPPLY RISK';
      statusText = `DEPLETION ${Math.abs(bufferDays).toFixed(1)}d BEFORE ETA`;
      color = '#c82a2a';
      badgeClass = 'red';
    } else if (bufferDays <= 7) {
      status = 'WATCH';
      statusText = `NARROW MARGIN (+${bufferDays.toFixed(1)}d)`;
      color = '#d9821a';
      badgeClass = 'amber';
    }

    return {
      category: cat.label,
      key: cat.key,
      minDays,
      bufferDays,
      status,
      statusText,
      color,
      badgeClass
    };
  });

  const overallRiskCount = coverageAnalysis.filter((c) => c.status === 'RESUPPLY RISK').length;
  const overallWatchCount = coverageAnalysis.filter((c) => c.status === 'WATCH').length;

  return (
    <section className="resupply-coverage-card" aria-label="Resupply Coverage Analysis">
      <div className="card-header-row">
        <div>
          <h2 className="card-title">RESUPPLY COVERAGE ANALYSIS</h2>
          <span className="card-subtitle">
            PROJECTED SUPPLY DEPLETION vs NEXT ARRIVAL ETA ({nextResupplyEta} DAYS)
          </span>
        </div>

        <div className="coverage-overall-badge">
          {overallRiskCount > 0 ? (
            <span className="status-pill red">
              ● CRITICAL: {overallRiskCount} CATEGORY AT RESUPPLY RISK
            </span>
          ) : overallWatchCount > 0 ? (
            <span className="status-pill amber">
              ● ADVISORY: {overallWatchCount} CATEGORY UNDER TIGHT BUFFER
            </span>
          ) : (
            <span className="status-pill sage">
              ● ALL KEY SUPPLIES COVERED UNTIL ARRIVAL
            </span>
          )}
        </div>
      </div>

      <div className="coverage-banner">
        <div className="coverage-mission-info">
          <span className="mission-tag">{missionId}</span>
          <span className="mission-transport">{transport}</span>
          <span className="mission-eta">NEXT DELIVERY: <strong>{nextResupplyEta} DAYS</strong></span>
        </div>
        <p className="coverage-explainer">
          Operational safety margins require station stores to sustain life support beyond the scheduled delivery date in case of polar blizzards or flight aborts.
        </p>
      </div>

      <div className="coverage-grid">
        {coverageAnalysis.map((item, idx) => (
          <div
            key={idx}
            className={`coverage-item-box ${item.badgeClass}`}
            style={{ borderLeftColor: item.color }}
          >
            <div className="coverage-top-row">
              <span className="coverage-cat-title">{item.category}</span>
              <span
                className={`coverage-status-tag ${item.badgeClass}`}
                style={{ color: item.color, borderColor: item.color }}
              >
                ● {item.status}
              </span>
            </div>

            <div className="coverage-days-row">
              <div className="days-col">
                <span className="days-label">SUPPLY REMAINING</span>
                <span className="days-val" style={{ color: item.minDays < nextResupplyEta ? '#c82a2a' : 'var(--polaris-text-primary)' }}>
                  {item.minDays.toFixed(1)} DAYS
                </span>
              </div>

              <div className="coverage-divider">vs</div>

              <div className="days-col">
                <span className="days-label">NEXT RESUPPLY</span>
                <span className="days-val">{nextResupplyEta} DAYS</span>
              </div>
            </div>

            <div className="coverage-margin-bar">
              <span className="margin-note" style={{ color: item.color }}>
                {item.statusText}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

export default ResupplyCoverageCard;
