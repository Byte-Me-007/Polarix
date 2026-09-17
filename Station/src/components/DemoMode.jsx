import React from 'react';
import { useStationTelemetry } from '../hooks/useStationTelemetry';
import { DEMO_SCENARIOS } from '../data/stationData';

export const DemoMode = () => {
  const { scenario: activeScenario, setScenario } = useStationTelemetry();

  const scenarios = [
    { key: 'NORMAL', label: 'NORMAL' },
    { key: 'STORM', label: 'STORM', isCrit: true },
    { key: 'SENSOR_FAILURE', label: 'SENSOR FAILURE' },
    { key: 'POWER_CRISIS', label: 'POWER CRISIS', isCrit: true },
    { key: 'SATELLITE_OUTAGE', label: 'SATELLITE OUTAGE', isCrit: true },
    { key: 'RECOVERY', label: 'RECOVERY' }
  ];

  const currentDesc = DEMO_SCENARIOS[activeScenario]?.description || 'Nominal operational state.';

  return (
    <section className="simulation-dock" id="simulation-control-dock">
      <div className="simulation-identity">
        <span className="simulation-title">SIMULATION CONTROL</span>
        <span className="simulation-subtext">DEMONSTRATION ENVIRONMENT // FRONTEND STATE ONLY</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', flex: 1, maxWidth: '720px' }}>
        <div className="simulation-buttons-row">
          {scenarios.map((sc) => {
            const isActive = activeScenario === sc.key;
            return (
              <button
                key={sc.key}
                type="button"
                className={`sim-btn ${isActive ? 'active' : ''} ${isActive && sc.isCrit ? 'critical' : ''}`}
                onClick={() => setScenario(sc.key)}
              >
                {sc.label}
              </button>
            );
          })}
        </div>

        <div style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--polaris-text-muted)' }}>
          ACTIVE PROFILE: <strong style={{ color: 'var(--polaris-text-primary)' }}>{activeScenario}</strong> — {currentDesc}
        </div>
      </div>
    </section>
  );
};

export default DemoMode;
