import React from 'react';

/**
 * EnergyOperatingMode
 * Microgrid operational configuration selector and status indicator.
 * Clearly emphasizes the currently active mode derived from station telemetry.
 */
export const EnergyOperatingMode = ({
  activeMode = 'NORMAL MICROGRID',
  onSelectMode
}) => {
  const modes = [
    {
      id: 'NORMAL MICROGRID',
      title: 'NORMAL MICROGRID',
      badge: 'AUTOMATED',
      desc: 'Automatic bus synchronization balancing renewable penetration with auxiliary CHP dispatch.',
      color: '#3f6e4a'
    },
    {
      id: 'RENEWABLE PRIORITY',
      title: 'RENEWABLE PRIORITY',
      badge: 'ECO MODE',
      desc: 'Solar arrays and wind turbines maximized; diesel gensets throttled down to idle/standby.',
      color: '#3f6e4a'
    },
    {
      id: 'DIESEL BACKUP',
      title: 'DIESEL BACKUP',
      badge: 'THERMAL BASE',
      desc: 'Heavy auxiliary generator plant engaged to sustain microgrid during polar night or dead calm.',
      color: '#b65a1f'
    },
    {
      id: 'POWER CONSERVATION',
      title: 'POWER CONSERVATION',
      badge: 'DEMAND MANAGEMENT',
      desc: 'Selective load shedding protocol active; non-critical scientific equipment heaters throttled.',
      color: '#d9821a'
    },
    {
      id: 'EMERGENCY POWER',
      title: 'EMERGENCY POWER',
      badge: 'CRITICAL BUS',
      desc: 'Battery bank sustaining critical environmental life support following auxiliary genset lockout.',
      color: '#c82a2a'
    }
  ];

  return (
    <section className="operating-mode-section" aria-label="Energy Operating Mode">
      <div className="card-header-row">
        <div>
          <h3 className="card-title">ENERGY OPERATING MODE</h3>
          <span className="card-subtitle">MICROGRID AUTONOMOUS DISPATCH REGIME</span>
        </div>
        <div className="active-mode-stamp">
          ACTIVE: <strong style={{ color: 'var(--polaris-text-primary)' }}>{activeMode}</strong>
        </div>
      </div>

      <div className="operating-modes-grid">
        {modes.map((m) => {
          const isActive = activeMode === m.id;
          return (
            <div
              key={m.id}
              className={`mode-card ${isActive ? 'active' : ''}`}
              onClick={() => onSelectMode && onSelectMode(m.id)}
              style={{
                borderColor: isActive ? m.color : undefined
              }}
            >
              <div className="mode-card-top">
                <span
                  className="mode-dot"
                  style={{ background: isActive ? m.color : '#8a929e' }}
                />
                <span className="mode-name">{m.title}</span>
                <span className="mode-badge" style={{ color: m.color, borderColor: m.color }}>
                  {m.badge}
                </span>
              </div>
              <p className="mode-desc">{m.desc}</p>
              {isActive && (
                <div className="mode-active-indicator" style={{ color: m.color }}>
                  ✓ CURRENT OPERATIONAL REGIME
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default EnergyOperatingMode;
