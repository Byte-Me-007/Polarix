import React from 'react';

/**
 * FuelReserveCard
 * Polar diesel fuel infrastructure monitoring: Bulk reserve tanks,
 * daily burn rates, total liter inventory, and logistical autonomy projection.
 */
export const FuelReserveCard = ({
  fuelReserve = 64,
  autonomyDays = 18.4,
  dailyBurnRate = 480,
  totalLiters = 53400,
  capacityLiters = 83400,
  dieselKw = 23.1,
  reserveStatus = 'SECURE'
}) => {
  const isLow = fuelReserve < 35;
  const statusColor = isLow ? '#d9821a' : '#3f6e4a';

  return (
    <section className="fuel-reserve-card" aria-label="Polar Fuel Reserves">
      <div className="card-header-row">
        <div>
          <h3 className="card-title">POLAR FUEL RESERVES</h3>
          <span className="card-subtitle">ARCTIC-GRADE KEROSENE / POLAR DIESEL</span>
        </div>
        <span
          className="fuel-status-badge"
          style={{ color: statusColor, borderColor: statusColor }}
        >
          ● {reserveStatus || 'DATA UNAVAILABLE'}
        </span>
      </div>

      <div className="fuel-main-grid">
        {/* Visual Tank Gauge */}
        <div className="fuel-gauge-box">
          <div className="fuel-soc-large" style={{ color: statusColor }}>
            {typeof fuelReserve === 'number' ? `${fuelReserve}%` : 'DATA UNAVAILABLE'}
          </div>
          <span className="fuel-soc-label">BULK STORAGE CAPACITY</span>

          <div className="fuel-level-track">
            <div
              className="fuel-level-fill"
              style={{
                width: `${typeof fuelReserve === 'number' ? fuelReserve : 0}%`,
                background: statusColor
              }}
            />
          </div>

          <div className="fuel-volume-sub">
            {totalLiters ? `${totalLiters.toLocaleString()} L / ${capacityLiters.toLocaleString()} L` : 'DATA UNAVAILABLE'}
          </div>
        </div>

        {/* Consumption & Autonomy Metrics */}
        <div className="fuel-metrics-grid">
          <div className="f-metric-item">
            <span className="f-metric-label">ESTIMATED AUTONOMY</span>
            <span className="f-metric-val">
              {typeof autonomyDays === 'number' ? `${autonomyDays.toFixed(1)} DAYS` : 'DATA UNAVAILABLE'}
            </span>
            <span className="f-metric-sub">Without resupply vessel</span>
          </div>

          <div className="f-metric-item">
            <span className="f-metric-label">DAILY BURN RATE</span>
            <span className="f-metric-val mono-val">
              {dailyBurnRate ? `${dailyBurnRate} L / DAY` : 'DATA UNAVAILABLE'}
            </span>
            <span className="f-metric-sub">Combined auxiliary gensets</span>
          </div>

          <div className="f-metric-item">
            <span className="f-metric-label">DIESEL OUTPUT</span>
            <span className="f-metric-val mono-val">
              {typeof dieselKw === 'number' ? `${dieselKw.toFixed(1)} kW` : 'DATA UNAVAILABLE'}
            </span>
            <span className="f-metric-sub">Thermal & electrical CHP generation</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default FuelReserveCard;
