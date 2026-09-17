import React from 'react';
import { useStationTelemetry } from '../hooks/useStationTelemetry';

export const HealthScore = () => {
  const { telemetry, alerts } = useStationTelemetry();
  const score = telemetry.healthScore || 94;
  const status = telemetry.healthStatus || 'HEALTHY';
  const categories = telemetry.healthCategories || [];

  // Determine alert load level
  const criticalCount = alerts.filter(a => a.severity === 'CRITICAL').length;
  const alertLoadText = criticalCount > 0 ? 'ELEVATED' : 'LOW';

  // SVG Radial Gauge parameters
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  const getReadinessTheme = (val) => {
    if (val >= 85) return { color: 'var(--status-normal)', bg: 'var(--status-normal-bg)' };
    if (val >= 60) return { color: 'var(--status-warning)', bg: 'var(--status-warning-bg)' };
    return { color: 'var(--status-critical)', bg: 'var(--status-critical-bg)' };
  };

  const theme = getReadinessTheme(score);

  // Category values mapping with case-insensitive search
  const getCategoryScore = (catName, defaultVal) => {
    const found = categories.find(c => c.name?.toUpperCase() === catName.toUpperCase());
    return found ? found.score : defaultVal;
  };

  const breakdownItems = [
    { name: 'ENVIRONMENT', val: getCategoryScore('ENVIRONMENT', 96), isNum: true },
    { name: 'ENERGY', val: getCategoryScore('ENERGY', 91), isNum: true },
    { name: 'STRUCTURE', val: getCategoryScore('STRUCTURE', 97), isNum: true },
    { name: 'CONNECTIVITY', val: getCategoryScore('CONNECTIVITY', 94), isNum: true },
    { 
      name: 'ALERT LOAD', 
      val: alertLoadText, 
      isNum: false, 
      color: criticalCount > 0 ? 'var(--status-critical)' : 'var(--polaris-sage)' 
    }
  ];

  return (
    <div className="readiness-module" id="station-readiness-panel">
      <div>
        <div className="section-label-tiny">STATION READINESS INDEX</div>

        <div className="readiness-dial-area">
          {/* Refined Radial Indicator */}
          <div style={{ position: 'relative', width: '96px', height: '96px' }}>
            <svg className="readiness-radial-svg" viewBox="0 0 96 96">
              <circle
                cx="48"
                cy="48"
                r={radius}
                stroke="var(--polaris-border)"
                strokeWidth="6"
                fill="none"
              />
              <circle
                cx="48"
                cy="48"
                r={radius}
                stroke={theme.color}
                strokeWidth="6"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="none"
                style={{ transition: 'stroke-dashoffset 0.8s cubic-bezier(0.2, 0.8, 0.2, 1)' }}
              />
            </svg>

            <div 
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <span className="readiness-score-number">{score}</span>
              <span className="readiness-score-total">/100</span>
            </div>
          </div>

          <div>
            <span 
              className="readiness-status-tag"
              style={{ color: theme.color, background: theme.bg, border: `1px solid ${theme.color}40` }}
            >
              {status}
            </span>
            <p style={{ fontSize: '0.7125rem', color: 'var(--polaris-text-muted)', lineHeight: 1.35, marginTop: '0.25rem' }}>
              Operational readiness composite weighted across 5 primary field subsystems.
            </p>
          </div>
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="readiness-breakdown-list">
        {breakdownItems.map((item) => (
          <div className="breakdown-row" key={item.name}>
            <span className="breakdown-name">{item.name}</span>
            {item.isNum ? (
              <>
                <div className="breakdown-bar-track">
                  <div 
                    className="breakdown-bar-fill"
                    style={{ 
                      width: `${item.val}%`, 
                      background: item.val >= 95 ? 'var(--polaris-text-secondary)' : 'var(--polaris-copper)' 
                    }} 
                  />
                </div>
                <span className="breakdown-val">{item.val}</span>
              </>
            ) : (
              <span 
                className="breakdown-val" 
                style={{ width: 'auto', color: item.color, fontWeight: 700 }}
              >
                {item.val}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default HealthScore;
