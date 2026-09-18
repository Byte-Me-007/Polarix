import React from 'react';

/**
 * PowerFlowDiagram
 * Crisp, 2-second comprehension power topology diagram:
 * Solar + Wind + Diesel -> Microgrid Core Bus <-> Battery Storage -> Station Load.
 * Directional flow indicators adapt to charging/discharging operational dynamics.
 */
export const PowerFlowDiagram = ({
  solarKw = 42.8,
  windKw = 18.4,
  dieselKw = 23.1,
  totalGenKw = 84.3,
  loadKw = 84.3,
  batterySoc = 78,
  batteryState = 'CHARGING',
  batteryCurrent = '+38.4 A'
}) => {
  const isCharging = batteryState.includes('CHARGING');
  const isDischarging = batteryState.includes('DISCHARGING');

  return (
    <section className="power-flow-section" aria-label="Power Flow Schematic">
      <div className="power-flow-header">
        <div className="flow-title-wrap">
          <h2 className="flow-title">MICROGRID POWER FLOW TOPOLOGY</h2>
          <span className="flow-subtitle">
            REAL-TIME ENERGY DISTRIBUTION // BUS FREQUENCY: 50.0 Hz
          </span>
        </div>
        <div className="flow-status-tag">
          <span className="flow-dot live" />
          <span>MICROGRID SYNCHRONIZED</span>
        </div>
      </div>

      <div className="flow-schematic-grid">
        {/* 1. Generation Sources Column */}
        <div className="flow-column sources-col">
          <div className="column-label">GENERATION SOURCES</div>

          {/* Solar Card */}
          <div className={`flow-node source-node ${solarKw > 0 ? 'active' : 'inactive'}`}>
            <div className="node-icon-row">
              <span className="node-type">SOLAR ARRAY</span>
              <span className={`node-badge ${solarKw > 0 ? 'sage' : 'muted'}`}>
                {solarKw > 0 ? 'ACTIVE' : 'STANDBY'}
              </span>
            </div>
            <div className="node-val-large">{solarKw.toFixed(1)} kW</div>
            <div className="node-sub-info">Photovoltaic Bus</div>
          </div>

          {/* Wind Card */}
          <div className={`flow-node source-node ${windKw > 0 ? 'active' : 'inactive'}`}>
            <div className="node-icon-row">
              <span className="node-type">WIND TURBINE</span>
              <span className={`node-badge ${windKw > 0 ? 'sage' : 'muted'}`}>
                {windKw > 0 ? 'ACTIVE' : 'STANDBY'}
              </span>
            </div>
            <div className="node-val-large">{windKw.toFixed(1)} kW</div>
            <div className="node-sub-info">Aerodynamic Alternator</div>
          </div>

          {/* Diesel Card */}
          <div className={`flow-node source-node ${dieselKw > 0 ? 'active' : 'inactive'}`}>
            <div className="node-icon-row">
              <span className="node-type">DIESEL GENSET</span>
              <span className={`node-badge ${dieselKw > 0 ? 'amber' : 'muted'}`}>
                {dieselKw > 0 ? 'RUNNING' : 'STANDBY'}
              </span>
            </div>
            <div className="node-val-large">{dieselKw.toFixed(1)} kW</div>
            <div className="node-sub-info">Combined Heat & Power</div>
          </div>
        </div>

        {/* 2. SVG Flow Lines: Sources -> Microgrid */}
        <div className="flow-connector-col">
          <svg className="flow-svg" viewBox="0 0 100 240" preserveAspectRatio="none">
            {/* Top Source to Center (Solar) */}
            <path
              d="M 10 40 C 50 40, 50 120, 90 120"
              fill="none"
              stroke={solarKw > 0 ? '#3f6e4a' : '#dcd5c9'}
              strokeWidth="2.5"
              strokeDasharray={solarKw > 0 ? '4 3' : 'none'}
              className={solarKw > 0 ? 'flow-pulse-forward' : ''}
            />
            {/* Middle Source to Center (Wind) */}
            <path
              d="M 10 120 L 90 120"
              fill="none"
              stroke={windKw > 0 ? '#3f6e4a' : '#dcd5c9'}
              strokeWidth="2.5"
              strokeDasharray={windKw > 0 ? '4 3' : 'none'}
              className={windKw > 0 ? 'flow-pulse-forward' : ''}
            />
            {/* Bottom Source to Center (Diesel) */}
            <path
              d="M 10 200 C 50 200, 50 120, 90 120"
              fill="none"
              stroke={dieselKw > 0 ? '#b65a1f' : '#dcd5c9'}
              strokeWidth="2.5"
              strokeDasharray={dieselKw > 0 ? '4 3' : 'none'}
              className={dieselKw > 0 ? 'flow-pulse-forward' : ''}
            />
          </svg>
        </div>

        {/* 3. Central Hub Column: Microgrid Bus & Battery */}
        <div className="flow-column center-hub-col">
          <div className="column-label">CENTRAL MICROGRID & STORAGE</div>

          {/* Battery Node (Connected to Microgrid) */}
          <div className={`flow-node battery-hub-node ${isDischarging ? 'discharging' : isCharging ? 'charging' : ''}`}>
            <div className="node-icon-row">
              <span className="node-type">LI-ION BATTERY STORAGE</span>
              <span className={`node-badge ${isDischarging ? 'red' : isCharging ? 'sage' : 'muted'}`}>
                {isCharging ? '↓ CHARGING' : isDischarging ? '↑ DISCHARGING' : 'FLOAT'}
              </span>
            </div>
            <div className="node-val-large">{batterySoc}%</div>
            <div className="node-sub-info">
              {batteryCurrent} • {batteryState}
            </div>
          </div>

          {/* Vertical Battery Flow Arrow */}
          <div className="battery-flow-link">
            <span className={`battery-arrow-icon ${isDischarging ? 'up' : isCharging ? 'down' : 'neutral'}`}>
              {isDischarging ? '▲ DISCHARGE BUS' : isCharging ? '▼ CHARGE BUS' : '◆ FLOAT BALANCED'}
            </span>
          </div>

          {/* Central Microgrid Hub Node */}
          <div className="flow-node microgrid-hub-node">
            <div className="node-icon-row">
              <span className="node-type">CORE MICROGRID BUS</span>
              <span className="node-badge sage">50.0 Hz</span>
            </div>
            <div className="node-val-large">{totalGenKw.toFixed(1)} kW</div>
            <div className="node-sub-info">Total Supply Ingestion</div>
          </div>
        </div>

        {/* 4. SVG Flow Lines: Microgrid -> Load */}
        <div className="flow-connector-col">
          <svg className="flow-svg" viewBox="0 0 100 240" preserveAspectRatio="none">
            <path
              d="M 10 200 L 90 200"
              fill="none"
              stroke="#191c20"
              strokeWidth="3"
              strokeDasharray="5 3"
              className="flow-pulse-forward"
            />
          </svg>
        </div>

        {/* 5. Destination: Station Demand Column */}
        <div className="flow-column load-col">
          <div className="column-label">FACILITY CONSUMPTION</div>

          <div className="flow-node load-destination-node">
            <div className="node-icon-row">
              <span className="node-type">TOTAL STATION DEMAND</span>
              <span className="node-badge copper">CRITICAL LOAD</span>
            </div>
            <div className="node-val-large">{loadKw.toFixed(1)} kW</div>
            <div className="node-sub-info">Habitats • Scientific Labs • Life Support</div>

            <div className="load-sub-meters">
              <div className="sub-meter-row">
                <span>LIFE SUPPORT & HVAC</span>
                <strong>{(loadKw * 0.48).toFixed(1)} kW</strong>
              </div>
              <div className="sub-meter-row">
                <span>SCIENTIFIC INSTRUMENTS</span>
                <strong>{(loadKw * 0.32).toFixed(1)} kW</strong>
              </div>
              <div className="sub-meter-row">
                <span>AUXILIARY & COMMS</span>
                <strong>{(loadKw * 0.20).toFixed(1)} kW</strong>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default PowerFlowDiagram;
