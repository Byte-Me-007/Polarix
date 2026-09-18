import React from 'react';

/**
 * ExecutiveEnergyStrip
 * Compact operational strip displaying the 6 vital energy metrics:
 * Current Load, Generation, Battery SOC, Fuel Reserve, Autonomy, and Renewable Share.
 */
export const ExecutiveEnergyStrip = ({
  loadKw = 84.3,
  totalGenKw = 84.3,
  batterySoc = 78,
  batteryState = 'CHARGING',
  fuelReserve = 64,
  autonomyDays = 18.4,
  renewableShare = 72
}) => {
  const isBatteryCrit = batterySoc <= 45 || batteryState.includes('CRITICAL');
  const isBatteryWarn = batterySoc <= 60 && !isBatteryCrit;

  const isFuelWarn = fuelReserve <= 35;

  const metrics = [
    {
      label: 'CURRENT LOAD',
      value: `${loadKw.toFixed(1)} kW`,
      sub: 'Station demand',
      color: 'var(--polaris-text-primary)'
    },
    {
      label: 'GENERATION',
      value: `${totalGenKw.toFixed(1)} kW`,
      sub: totalGenKw >= loadKw ? 'Balanced supply' : 'Deficit / discharging',
      color: totalGenKw >= loadKw ? '#3f6e4a' : '#d9821a'
    },
    {
      label: 'BATTERY SOC',
      value: `${batterySoc}%`,
      sub: batteryState,
      color: isBatteryCrit ? '#c82a2a' : isBatteryWarn ? '#d9821a' : '#3f6e4a'
    },
    {
      label: 'FUEL RESERVE',
      value: `${fuelReserve}%`,
      sub: 'Bulk tank volume',
      color: isFuelWarn ? '#d9821a' : 'var(--polaris-text-primary)'
    },
    {
      label: 'AUTONOMY',
      value: `${autonomyDays.toFixed(1)} DAYS`,
      sub: 'At current burn rate',
      color: autonomyDays < 30 ? '#d9821a' : '#3f6e4a'
    },
    {
      label: 'RENEWABLE SHARE',
      value: `${renewableShare}%`,
      sub: 'Solar + Wind contribution',
      color: renewableShare >= 65 ? '#3f6e4a' : renewableShare >= 40 ? '#b65a1f' : '#727b87'
    }
  ];

  return (
    <div className="executive-energy-strip" role="region" aria-label="Executive Energy Metrics">
      {metrics.map((m, idx) => (
        <div key={idx} className="energy-metric-card">
          <span className="energy-metric-label">{m.label}</span>
          <span className="energy-metric-val" style={{ color: m.color }}>
            {m.value}
          </span>
          <span className="energy-metric-sub">{m.sub}</span>
        </div>
      ))}
    </div>
  );
};

export default ExecutiveEnergyStrip;
