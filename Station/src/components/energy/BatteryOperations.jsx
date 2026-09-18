import React from 'react';

/**
 * BatteryOperations
 * Industrial battery analytics display: State of charge, physical cell metrics,
 * cycle count, health, and dynamic charge/discharge visualization.
 */
export const BatteryOperations = ({
  batterySoc = 78,
  batteryState = 'CHARGING',
  voltage = '418.2 V',
  current = '+38.4 A',
  remainingHours = '38.5 hrs',
  health = '98.2%',
  cycles = 1420,
  batteryLowThreshold = 45
}) => {
  const isCrit = batterySoc <= batteryLowThreshold || batteryState.includes('CRITICAL');
  const isWarn = batterySoc <= 60 && !isCrit;
  const isCharging = batteryState.includes('CHARGING');
  const isDischarging = batteryState.includes('DISCHARGING');

  const statusColor = isCrit ? '#c82a2a' : isWarn || isDischarging ? '#d9821a' : '#3f6e4a';

  return (
    <section className="battery-operations-card" aria-label="Battery Storage Operations">
      <div className="card-header-row">
        <div>
          <h3 className="card-title">BATTERY STORAGE OPERATIONS</h3>
          <span className="card-subtitle">INDUSTRIAL LiFePO4 SUBSTATION BANK</span>
        </div>
        <span
          className="battery-status-badge"
          style={{ color: statusColor, borderColor: statusColor }}
        >
          ● {batteryState}
        </span>
      </div>

      <div className="battery-main-grid">
        {/* Visual Battery Gauge */}
        <div className="battery-gauge-box">
          <div className="battery-soc-large" style={{ color: statusColor }}>
            {batterySoc}%
          </div>
          <span className="battery-soc-label">STATE OF CHARGE</span>

          {/* Segmented / Smooth Polar Battery Level Bar */}
          <div className="battery-level-track">
            <div
              className="battery-level-fill"
              style={{
                width: `${batterySoc}%`,
                background: statusColor
              }}
            />
          </div>

          <div className="battery-direction-hint">
            {isCharging && '▲ INGESTING SOLAR / DIESEL EXCESS'}
            {isDischarging && '▼ SUSTAINING CRITICAL LIFE-SUPPORT BUS'}
            {!isCharging && !isDischarging && '◆ FLOAT BALANCED AT MAXIMUM SOC'}
          </div>
        </div>

        {/* Battery Telemetry Parameters */}
        <div className="battery-metrics-grid">
          <div className="b-metric-item">
            <span className="b-metric-label">REMAINING RUNTIME</span>
            <span className="b-metric-val">{remainingHours}</span>
            <span className="b-metric-sub">At current discharge curve</span>
          </div>

          <div className="b-metric-item">
            <span className="b-metric-label">BANK VOLTAGE</span>
            <span className="b-metric-val mono-val">{voltage}</span>
            <span className="b-metric-sub">Nominal 400V DC Bus</span>
          </div>

          <div className="b-metric-item">
            <span className="b-metric-label">NET CURRENT</span>
            <span className="b-metric-val mono-val" style={{ color: statusColor }}>
              {current}
            </span>
            <span className="b-metric-sub">Bidirectional inverter shunt</span>
          </div>

          <div className="b-metric-item">
            <span className="b-metric-label">BATTERY HEALTH (SOH)</span>
            <span className="b-metric-val mono-val">{health}</span>
            <span className="b-metric-sub">{cycles} Completed cycles</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default BatteryOperations;
