import React from 'react';

/**
 * ExecutiveLogisticsStrip
 * Compact operational strip displaying 5 core logistics indicators:
 * TOTAL INVENTORY, CRITICAL STOCK, DAYS OF SUPPLY, INCOMING CARGO, STORAGE UTILIZATION.
 */
export const ExecutiveLogisticsStrip = ({
  totalInventoryTons = 128.4,
  criticalStockCount = 3,
  daysOfSupply = 18.4,
  incomingCargoTons = 18.6,
  storageUtilization = 68
}) => {
  const isDaysCrit = daysOfSupply < 20;
  const isDaysWarn = daysOfSupply < 35 && !isDaysCrit;

  const metrics = [
    {
      label: 'TOTAL INVENTORY',
      value: `${totalInventoryTons.toFixed(1)} t`,
      sub: 'All station active stores',
      color: 'var(--polaris-text-primary)'
    },
    {
      label: 'CRITICAL STOCK',
      value: criticalStockCount < 10 ? `0${criticalStockCount} ITEMS` : `${criticalStockCount} ITEMS`,
      sub: criticalStockCount > 0 ? 'Requires priority monitoring' : 'Nominal stock buffers',
      color: criticalStockCount > 0 ? (criticalStockCount > 2 ? '#c82a2a' : '#d9821a') : '#3f6e4a'
    },
    {
      label: 'DAYS OF SUPPLY',
      value: `${daysOfSupply.toFixed(1)} DAYS`,
      sub: 'Constrained supply baseline',
      color: isDaysCrit ? '#c82a2a' : isDaysWarn ? '#d9821a' : '#3f6e4a'
    },
    {
      label: 'INCOMING CARGO',
      value: `${incomingCargoTons.toFixed(1)} t`,
      sub: 'En-route / scheduled cargo',
      color: 'var(--polaris-copper)'
    },
    {
      label: 'STORAGE UTILIZATION',
      value: `${storageUtilization}%`,
      sub: 'Aggregate bunker capacity',
      color: storageUtilization > 85 ? '#d9821a' : 'var(--polaris-text-primary)'
    }
  ];

  return (
    <div className="executive-logistics-strip" role="region" aria-label="Executive Logistics Metrics">
      {metrics.map((m, idx) => (
        <div key={idx} className="logistics-metric-card">
          <span className="logistics-metric-label">{m.label}</span>
          <span className="logistics-metric-val" style={{ color: m.color }}>
            {m.value}
          </span>
          <span className="logistics-metric-sub">{m.sub}</span>
        </div>
      ))}
    </div>
  );
};

export default ExecutiveLogisticsStrip;
