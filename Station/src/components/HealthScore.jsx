import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMissionReadiness } from '../hooks/useMissionReadiness';
import { MissionReadinessDrawer } from './readiness/MissionReadinessDrawer';

/**
 * HealthScore (Station Mission Readiness Executive Console)
 * 
 * Provides an immediate operational answer to:
 * "Can the station currently operate safely and effectively?"
 * Displays:
 * 1. Overall Readiness: READY / DEGRADED / AT RISK
 * 2. Major contributing systems: POWER, COMMUNICATIONS, INFRASTRUCTURE, SUPPLIES, ALERTS
 * 3. Operational causes with direct action links (Energy, Logistics, Alerts, Digital Twin)
 * 4. Expandable full traceability drawer
 */
export const HealthScore = () => {
  const navigate = useNavigate();
  const readiness = useMissionReadiness();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const {
    overallReadiness,
    overallSummary,
    overallTheme,
    systems = [],
    causes = [],
    activeStation
  } = readiness;

  const handleAction = (cause) => {
    if (cause.actionLabel.includes('DIGITAL TWIN') || cause.actionRoute === '/digital-twin') {
      navigate('/digital-twin', {
        state: {
          focusZone: cause.twinZone,
          locateSensorId: cause.sensorId,
          twinMode: 'XRAY'
        }
      });
    } else {
      navigate(cause.actionRoute, {
        state: {
          focusZone: cause.twinZone,
          severityFilter: cause.severity === 'CRITICAL' ? 'CRITICAL' : 'ALL'
        }
      });
    }
  };

  const renderMeter = (system) => {
    const totalSegments = 8;
    const filledSegments = Math.max(1, Math.round((system.rating / 100) * totalSegments));
    const isCrit = system.status === 'CRITICAL';
    const isDeg = system.status === 'DEGRADED' || system.status === 'LOW';

    let segmentColor = 'var(--polaris-sage)';
    if (isCrit) segmentColor = 'var(--polaris-red)';
    else if (isDeg) segmentColor = 'var(--polaris-amber)';

    return (
      <div className="panel-meter-wrap" title={`${system.name}: ${system.status}`}>
        <div className="panel-meter-blocks">
          {Array.from({ length: totalSegments }).map((_, idx) => (
            <span
              key={idx}
              className="panel-meter-block"
              style={{
                background: idx < filledSegments ? segmentColor : 'var(--polaris-border)',
                opacity: idx < filledSegments ? 1 : 0.35
              }}
            />
          ))}
        </div>
        <span
          className="panel-meter-status"
          style={{ color: segmentColor }}
        >
          {system.badge || system.status}
        </span>
      </div>
    );
  };

  return (
    <>
      <div className="readiness-module" id="station-readiness-panel">
        {/* PANEL HEADER */}
        <div className="readiness-panel-top">
          <div className="readiness-panel-headline">
            <span className="section-label-tiny">MISSION READINESS // {activeStation}</span>
            <div 
              className="readiness-status-pill"
              style={{
                color: overallTheme.badgeText,
                background: overallTheme.badgeBg,
                borderColor: overallTheme.border
              }}
              onClick={() => setIsDrawerOpen(true)}
              title="Click to expand operational readiness breakdown"
            >
              <span 
                className="readiness-status-dot" 
                style={{ background: overallTheme.badgeText }} 
              />
              <span className="readiness-status-text">{overallReadiness}</span>
            </div>
          </div>
          <p className="readiness-operational-prompt">
            "Can the station currently operate safely and effectively?"
          </p>
          <p className="readiness-operational-summary">
            {overallSummary}
          </p>
        </div>

        {/* CONTRIBUTING SYSTEMS COMPACT GAUGES */}
        <div className="readiness-contributing-list">
          {systems.map((sys) => (
            <div 
              key={sys.id} 
              className="readiness-panel-sys-row"
              onClick={() => {
                if (sys.targetRoute === '/digital-twin') {
                  navigate('/digital-twin', { state: { focusZone: sys.twinZone, twinMode: 'SYSTEM' } });
                } else {
                  navigate(sys.targetRoute);
                }
              }}
              title={`Inspect ${sys.name} in ${sys.source}`}
            >
              <span className="readiness-panel-sys-name">{sys.name}</span>
              {renderMeter(sys)}
            </div>
          ))}
        </div>

        {/* CAUSES SECTION: SHOW ACTUAL REASONS AFFECTING READINESS */}
        <div className="readiness-causes-compact">
          <div className="readiness-causes-header">
            <span className="causes-title-label">
              {causes.length > 0 ? 'CAUSES AFFECTING READINESS:' : 'OPERATIONAL CONDITION:'}
            </span>
          </div>

          {causes.length === 0 ? (
            <div className="readiness-causes-nominal">
              <span className="nominal-check">✓</span>
              <span>All primary life-support, power, logistics, and comms nominal.</span>
            </div>
          ) : (
            <ul className="readiness-causes-bullets">
              {causes.slice(0, 3).map((cause) => (
                <li key={cause.id} className="readiness-cause-item">
                  <div className="cause-item-left">
                    <span className={`cause-bullet-dot cause-dot-${cause.severity.toLowerCase()}`} />
                    <span className="cause-item-text" title={cause.title}>
                      {cause.title}
                    </span>
                  </div>
                  <div className="cause-item-btns">
                    <button
                      className="cause-action-link"
                      onClick={() => handleAction(cause)}
                      title={cause.actionLabel}
                    >
                      {cause.actionLabel} →
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* FOOTER ACTION */}
        <div className="readiness-panel-footer">
          <button 
            className="readiness-expand-btn"
            onClick={() => setIsDrawerOpen(true)}
          >
            <span>EXPAND READINESS BREAKDOWN</span>
            <span>↗</span>
          </button>
        </div>
      </div>

      {/* EXPANDABLE FULL TRACEABILITY DRAWER */}
      <MissionReadinessDrawer 
        isOpen={isDrawerOpen} 
        onClose={() => setIsDrawerOpen(false)} 
      />
    </>
  );
};

export default HealthScore;
