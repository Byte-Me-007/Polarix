import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { useMissionReadiness } from '../../hooks/useMissionReadiness';

export const MissionReadinessDrawer = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const readiness = useMissionReadiness();
  const [showFullTraceability, setShowFullTraceability] = useState(false);

  // Close drawer on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const {
    overallReadiness,
    overallSummary,
    overallTheme,
    systems,
    causes,
    traceabilityMatrix,
    stationName,
    activeStation
  } = readiness;

  const handleAction = (cause) => {
    onClose();
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

  const handleSystemNavigate = (system) => {
    onClose();
    if (system.targetRoute === '/digital-twin') {
      navigate('/digital-twin', {
        state: {
          focusZone: system.twinZone,
          twinMode: 'SYSTEM'
        }
      });
    } else {
      navigate(system.targetRoute);
    }
  };

  // Render a clean segmented meter for system status (e.g. ████████)
  const renderMeter = (system) => {
    const totalSegments = 8;
    const filledSegments = Math.max(1, Math.round((system.rating / 100) * totalSegments));
    const isCrit = system.status === 'CRITICAL';
    const isDeg = system.status === 'DEGRADED' || system.status === 'LOW';

    let segmentColor = 'var(--polaris-sage)';
    if (isCrit) segmentColor = 'var(--polaris-red)';
    else if (isDeg) segmentColor = 'var(--polaris-amber)';

    return (
      <div className="readiness-meter-container" title={`${system.name}: ${system.status} (${system.reason})`}>
        <div className="readiness-meter-blocks">
          {Array.from({ length: totalSegments }).map((_, idx) => (
            <span
              key={idx}
              className="readiness-meter-block"
              style={{
                background: idx < filledSegments ? segmentColor : 'var(--polaris-border)',
                opacity: idx < filledSegments ? 1 : 0.35
              }}
            />
          ))}
        </div>
        <span
          className="readiness-meter-badge"
          style={{
            color: segmentColor,
            fontWeight: 700
          }}
        >
          {system.badge || system.status}
        </span>
      </div>
    );
  };

  return createPortal(
    <div className="mission-readiness-backdrop" onClick={onClose}>
      <div 
        className="mission-readiness-drawer" 
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Mission Readiness and Operations Panel"
      >
        {/* DRAWER HEADER */}
        <div className="readiness-drawer-header">
          <div>
            <div className="readiness-station-tag">
              POLARIS // {activeStation} STATION
            </div>
            <h2 className="readiness-drawer-title">MISSION READINESS</h2>
            <div className="readiness-drawer-question">
              "Can the station currently operate safely and effectively?"
            </div>
          </div>
          <button 
            className="readiness-drawer-close"
            onClick={onClose}
            aria-label="Close mission readiness panel"
          >
            ✕
          </button>
        </div>

        <div className="readiness-drawer-body">
          {/* PRIMARY OVERALL STATUS HERO */}
          <div 
            className="readiness-status-hero"
            style={{
              borderColor: overallTheme.border,
              background: overallTheme.badgeBg
            }}
          >
            <div className="readiness-hero-left">
              <span className="readiness-hero-label">STATION OPERATIONAL STATUS</span>
              <div 
                className="readiness-hero-badge"
                style={{
                  color: overallTheme.badgeText,
                  background: overallTheme.badgeBg,
                  borderColor: overallTheme.border
                }}
              >
                <span 
                  className="readiness-hero-dot" 
                  style={{ background: overallTheme.badgeText }} 
                />
                {overallReadiness}
              </div>
            </div>
            <p className="readiness-hero-summary">
              {overallSummary}
            </p>
          </div>

          {/* CONTRIBUTING SYSTEMS COMPACT PANEL */}
          <div className="readiness-section">
            <div className="readiness-section-header">
              <span className="readiness-section-title">MAJOR CONTRIBUTING SYSTEMS</span>
              <span className="readiness-section-sub">REAL-TIME SUBSYSTEM STATUS</span>
            </div>

            <div className="readiness-systems-list">
              {systems.map((sys) => (
                <div 
                  key={sys.id} 
                  className="readiness-system-row"
                  onClick={() => handleSystemNavigate(sys)}
                  title={`Inspect ${sys.name} in ${sys.source}`}
                >
                  <div className="readiness-system-meta">
                    <span className="readiness-system-name">{sys.name}</span>
                    <span className="readiness-system-src">SOURCE: {sys.source}</span>
                  </div>
                  {renderMeter(sys)}
                </div>
              ))}
            </div>
          </div>

          {/* CAUSES SECTION (THE MOST IMPORTANT PART) */}
          <div className="readiness-section">
            <div className="readiness-section-header">
              <span className="readiness-section-title">
                {causes.length > 0 ? 'ACTIVE OPERATIONAL CAUSES' : 'OPERATIONAL CONDITION'}
              </span>
              <span className="readiness-section-sub">
                {causes.length > 0 ? `${causes.length} FACTOR${causes.length > 1 ? 'S' : ''} DETECTED` : 'ALL SYSTEMS NOMINAL'}
              </span>
            </div>

            {causes.length === 0 ? (
              <div className="readiness-causes-empty">
                <span className="readiness-empty-icon">✓</span>
                <div>
                  <div className="readiness-empty-title">Zero Operational Bottlenecks Detected</div>
                  <div className="readiness-empty-desc">
                    Microgrid balance, satellite telemetry, environmental load, and fuel reserves are within designated safety envelopes.
                  </div>
                </div>
              </div>
            ) : (
              <div className="readiness-causes-list">
                {causes.map((cause) => (
                  <div 
                    key={cause.id} 
                    className={`readiness-cause-card readiness-cause-${cause.severity.toLowerCase()}`}
                  >
                    <div className="readiness-cause-main">
                      <div className="readiness-cause-indicator" />
                      <div className="readiness-cause-content">
                        <div className="readiness-cause-title">{cause.title}</div>
                        <div className="readiness-cause-meta">
                          <span>SYSTEM: {cause.system}</span>
                          <span>•</span>
                          <span>SOURCE: {cause.source}</span>
                          {cause.twinZone && (
                            <>
                              <span>•</span>
                              <span>ZONE: {cause.twinZone}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="readiness-cause-actions">
                      <button
                        className="readiness-action-btn"
                        onClick={() => handleAction(cause)}
                      >
                        {cause.actionLabel} →
                      </button>
                      {cause.twinZone && cause.actionLabel !== 'LOCATE IN DIGITAL TWIN' && (
                        <button
                          className="readiness-twin-btn"
                          title="Locate asset in 3D Digital Twin"
                          onClick={() => {
                            onClose();
                            navigate('/digital-twin', {
                              state: {
                                focusZone: cause.twinZone,
                                locateSensorId: cause.sensorId,
                                twinMode: 'XRAY'
                              }
                            });
                          }}
                        >
                          LOCATE IN TWIN ⌖
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* FULL TRACEABILITY MATRIX (COLLAPSIBLE) */}
          <div className="readiness-section">
            <div 
              className="readiness-accordion-toggle"
              onClick={() => setShowFullTraceability(prev => !prev)}
            >
              <span className="readiness-section-title">
                {showFullTraceability ? '▼ HIDE TRACEABILITY MATRIX' : '▶ VIEW SYSTEM TRACEABILITY BREAKDOWN'}
              </span>
              <span className="readiness-section-sub">SYSTEM // STATUS // REASON // SOURCE</span>
            </div>

            {showFullTraceability && (
              <div className="readiness-traceability-table-wrapper">
                <table className="readiness-traceability-table">
                  <thead>
                    <tr>
                      <th>SYSTEM</th>
                      <th>STATUS</th>
                      <th>PRIMARY REASON</th>
                      <th>SOURCE</th>
                      <th>INVESTIGATE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {traceabilityMatrix.map((row) => (
                      <tr key={row.system}>
                        <td className="trace-cell-system">{row.system}</td>
                        <td className="trace-cell-status">
                          <span className={`trace-status-tag trace-tag-${row.status.toLowerCase()}`}>
                            {row.status}
                          </span>
                        </td>
                        <td className="trace-cell-reason">{row.reason}</td>
                        <td className="trace-cell-source">{row.source}</td>
                        <td className="trace-cell-action">
                          <button
                            className="trace-link-btn"
                            onClick={() => {
                              onClose();
                              navigate(row.action);
                            }}
                          >
                            OPEN →
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* DRAWER FOOTER */}
        <div className="readiness-drawer-footer">
          <span className="readiness-footer-note">
            Telemetry synchronized with active station context. No synthetic scores.
          </span>
          <button className="readiness-footer-close-btn" onClick={onClose}>
            DISMISS PANEL
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default MissionReadinessDrawer;
