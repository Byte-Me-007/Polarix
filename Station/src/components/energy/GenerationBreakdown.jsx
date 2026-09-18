import React from 'react';

/**
 * GenerationBreakdown
 * Displays specific power outputs, dynamically calculated percentage shares,
 * and operational status for Solar, Wind, and Diesel generation.
 */
export const GenerationBreakdown = ({
  solarKw = 42.8,
  windKw = 18.4,
  dieselKw = 23.1,
  totalGenKw = 84.3
}) => {
  const safeTotal = totalGenKw > 0 ? totalGenKw : 0.001;

  const solarPct = Math.round((solarKw / safeTotal) * 100);
  const windPct = Math.round((windKw / safeTotal) * 100);
  const dieselPct = Math.max(0, 100 - solarPct - windPct);

  const sources = [
    {
      name: 'SOLAR PHOTOVOLTAIC',
      kw: solarKw,
      pct: solarPct,
      state: solarKw > 0 ? 'ACTIVE' : 'STANDBY',
      sub: 'Bifacial polar solar arrays',
      color: '#3f6e4a',
      bgBar: 'rgba(63, 110, 74, 0.85)'
    },
    {
      name: 'WIND TURBINE GENERATOR',
      kw: windKw,
      pct: windPct,
      state: windKw > 0 ? 'ACTIVE' : 'STANDBY',
      sub: 'Heavy-duty polar wind turbines',
      color: '#b65a1f',
      bgBar: 'rgba(182, 90, 31, 0.85)'
    },
    {
      name: 'DIESEL AUXILIARY CHP',
      kw: dieselKw,
      pct: dieselPct,
      state: dieselKw > 0 ? 'SYNCHRONIZED' : 'OFFLINE / STANDBY',
      sub: 'DG Unit #1 & #2 heat recovery',
      color: dieselKw > 0 ? '#d9821a' : '#727b87',
      bgBar: 'rgba(217, 130, 26, 0.85)'
    }
  ];

  return (
    <section className="generation-breakdown-card" aria-label="Generation Sources Breakdown">
      <div className="card-header-row">
        <h3 className="card-title">GENERATION MIX BREAKDOWN</h3>
        <span className="card-tag">TOTAL: {totalGenKw.toFixed(1)} kW</span>
      </div>

      {/* Proportional Stacked Bar */}
      <div className="proportional-gen-bar" title="Proportional energy source contribution">
        <div style={{ width: `${solarPct}%`, background: '#3f6e4a' }} title={`Solar: ${solarPct}%`} />
        <div style={{ width: `${windPct}%`, background: '#b65a1f' }} title={`Wind: ${windPct}%`} />
        <div style={{ width: `${dieselPct}%`, background: '#d9821a' }} title={`Diesel: ${dieselPct}%`} />
      </div>

      {/* Sources Details Grid */}
      <div className="sources-detail-grid">
        {sources.map((s, idx) => (
          <div key={idx} className="source-item-box">
            <div className="source-item-header">
              <span className="source-item-name">{s.name}</span>
              <span className="source-item-badge" style={{ color: s.color, borderColor: s.color }}>
                ● {s.state}
              </span>
            </div>

            <div className="source-item-metrics">
              <span className="source-kw">{s.kw.toFixed(1)} kW</span>
              <span className="source-pct" style={{ color: s.color }}>
                {s.pct}% OF SUPPLY
              </span>
            </div>

            <div className="source-item-sub">{s.sub}</div>
          </div>
        ))}
      </div>
    </section>
  );
};

export default GenerationBreakdown;
