import React from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * FuelLogisticsCard
 * Focused fuel logistics overview: reserves, daily burn rates, depletion horizon,
 * and delivery ETA, with quick deep link to /energy.
 */
export const FuelLogisticsCard = ({
  fuelReservePct = 64,
  totalLiters = 53400,
  capacityLiters = 83400,
  dailyBurnRate = 480,
  remainingDays = 18.4,
  nextDeliveryEta = 32
}) => {
  const navigate = useNavigate();

  const isLow = fuelReservePct < 35 || remainingDays < nextDeliveryEta;
  const statusColor = isLow ? '#d9821a' : '#3f6e4a';

  return (
    <section className="fuel-logistics-card" aria-label="Fuel Logistics Operations">
      <div className="card-header-row">
        <div>
          <h3 className="card-title">POLAR FUEL LOGISTICS</h3>
          <span className="card-subtitle">
            BULK DIESEL SUPPLY & STRATEGIC DEPLETION TRACKING
          </span>
        </div>
        <button
          type="button"
          className="view-in-energy-btn"
          onClick={() => navigate('/energy')}
        >
          VIEW IN ENERGY →
        </button>
      </div>

      <div className="fuel-logistics-grid">
        {/* Main Fuel Summary Box */}
        <div className="fuel-kpi-box">
          <div className="fuel-kpi-val" style={{ color: statusColor }}>
            {fuelReservePct}%
          </div>
          <span className="fuel-kpi-label">CURRENT RESERVE LEVEL</span>
          <div className="fuel-bar-track">
            <div
              className="fuel-bar-fill"
              style={{
                width: `${fuelReservePct}%`,
                background: statusColor
              }}
            />
          </div>
          <span className="fuel-liters-sub">
            {totalLiters.toLocaleString()} L / {capacityLiters.toLocaleString()} L
          </span>
        </div>

        {/* Detailed Metrics */}
        <div className="fuel-metrics-stack">
          <div className="fuel-m-row">
            <span className="f-label">DAILY CONSUMPTION</span>
            <span className="f-val">{dailyBurnRate} L / DAY</span>
          </div>

          <div className="fuel-m-row">
            <span className="f-label">PROJECTED AUTONOMY</span>
            <span className="f-val" style={{ color: statusColor }}>
              {remainingDays.toFixed(1)} DAYS
            </span>
          </div>

          <div className="fuel-m-row">
            <span className="f-label">NEXT FUEL TANKER ETA</span>
            <span className="f-val">{nextDeliveryEta} DAYS</span>
          </div>

          <div className="fuel-m-row highlight">
            <span className="f-label">DELIVERY BUFFER</span>
            <span className="f-val" style={{ color: remainingDays < nextDeliveryEta ? '#c82a2a' : '#3f6e4a' }}>
              {remainingDays < nextDeliveryEta
                ? `DEFICIT WARNING (${(nextDeliveryEta - remainingDays).toFixed(1)}d SHORT)`
                : `+${(remainingDays - nextDeliveryEta).toFixed(1)}d SURPLUS BUFFER`}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default FuelLogisticsCard;
