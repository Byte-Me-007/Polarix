import React from 'react';
import { useNavigate } from 'react-router-dom';

export const QuickActions = () => {
  const navigate = useNavigate();

  const commands = [
    {
      title: 'OPEN DIGITAL TWIN',
      sub: '3D STRUCTURAL & THERMAL MODEL',
      path: '/digital-twin',
      isPrimary: true
    },
    {
      title: 'ENERGY ANALYSIS',
      sub: 'MICROGRID & GENERATION DISPATCH',
      path: '/energy',
      isPrimary: false
    },
    {
      title: 'LOGISTICS FORECAST',
      sub: 'FUEL RESERVES & AUTONOMY',
      path: '/logistics',
      isPrimary: false
    },
    {
      title: 'EVENT TIMELINE',
      sub: 'COMPREHENSIVE TELEMETRY LOGS',
      path: '/alerts',
      isPrimary: false
    }
  ];

  return (
    <div className="commands-module" id="command-controls-panel">
      <div className="section-label-tiny" style={{ marginBottom: '0.4rem' }}>
        OPERATIONAL COMMAND CONTROLS
      </div>

      <div className="command-buttons-stack">
        {commands.map((cmd) => (
          <button
            key={cmd.title}
            type="button"
            className={`command-btn ${cmd.isPrimary ? 'primary-command' : ''}`}
            onClick={() => navigate(cmd.path)}
          >
            <div>
              <div>{cmd.title}</div>
              <div className="command-subtext">{cmd.sub}</div>
            </div>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>→</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default QuickActions;
