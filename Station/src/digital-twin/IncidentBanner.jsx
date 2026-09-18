/**
 * IncidentBanner.jsx
 *
 * Compact incident notification banner that appears at the top of the 3D viewport
 * when an operational incident is active.
 *
 * Design principles:
 *  - Compact — does not occupy more than ~36px height
 *  - Professional amber/copper color language (NOT garish neon)
 *  - Dismissible
 *  - Shows: scenario name, severity, affected system count
 */

import React from 'react';

const SEVERITY_STYLES = {
  CRITICAL: {
    background: 'linear-gradient(90deg, rgba(24,16,12,0.97) 0%, rgba(40,18,12,0.97) 100%)',
    border:     'rgba(181,56,43,0.65)',
    dot:        '#e53e3e',
    badge:      { bg: 'rgba(181,56,43,0.22)', color: '#e53e3e', border: 'rgba(181,56,43,0.5)' },
    label:      '#f0ece4',
    accent:     '#b5382b',
  },
  WARNING: {
    background: 'linear-gradient(90deg, rgba(22,18,10,0.97) 0%, rgba(38,26,8,0.97) 100%)',
    border:     'rgba(217,119,6,0.55)',
    dot:        '#d97706',
    badge:      { bg: 'rgba(217,119,6,0.18)', color: '#d97706', border: 'rgba(217,119,6,0.45)' },
    label:      '#f0ece4',
    accent:     '#d97706',
  },
  INFO: {
    background: 'rgba(22,26,34,0.95)',
    border:     'rgba(100,116,132,0.4)',
    dot:        '#64748b',
    badge:      { bg: 'rgba(100,116,132,0.14)', color: '#94a3b8', border: 'rgba(100,116,132,0.35)' },
    label:      '#c4c9d4',
    accent:     '#64748b',
  },
};

export const IncidentBanner = ({
  incidentGraph,
  onDismiss,
}) => {
  if (!incidentGraph?.isActive) return null;

  const { scenarioLabel, scenarioBadge, scenarioSeverity, affectedAssets, nodes } = incidentGraph;
  const sev = scenarioSeverity || 'WARNING';
  const styles = SEVERITY_STYLES[sev] || SEVERITY_STYLES.WARNING;

  const affectedCount = new Set(
    (nodes || []).map(n => n.zoneCode).filter(Boolean)
  ).size;

  return (
    <div
      style={{
        position: 'absolute',
        top: '8px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 90,
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        background: styles.background,
        border: `1px solid ${styles.border}`,
        borderRadius: '5px',
        padding: '5px 14px 5px 10px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.55)',
        backdropFilter: 'blur(4px)',
        minWidth: '240px',
        maxWidth: '420px',
        pointerEvents: 'auto',
      }}
    >
      {/* Pulse dot */}
      <span style={{
        width: '7px',
        height: '7px',
        borderRadius: '50%',
        background: styles.dot,
        flexShrink: 0,
        boxShadow: `0 0 6px ${styles.dot}88`,
      }} />

      {/* Scenario name */}
      <span style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: '10px',
        fontWeight: 800,
        letterSpacing: '0.08em',
        color: styles.label,
        whiteSpace: 'nowrap',
      }}>
        {scenarioLabel}
      </span>

      {/* Severity badge */}
      <span style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: '8px',
        fontWeight: 700,
        letterSpacing: '0.1em',
        color: styles.badge.color,
        background: styles.badge.bg,
        border: `1px solid ${styles.badge.border}`,
        borderRadius: '3px',
        padding: '1px 5px',
        whiteSpace: 'nowrap',
      }}>
        {sev}
      </span>

      {/* Divider */}
      <span style={{ color: styles.border, fontSize: '12px', lineHeight: 1 }}>·</span>

      {/* Affected count */}
      <span style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: '8.5px',
        fontWeight: 600,
        color: '#7a8394',
        whiteSpace: 'nowrap',
      }}>
        {affectedCount} {affectedCount === 1 ? 'system' : 'systems'} affected
      </span>

      {/* Dismiss button */}
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          title="Dismiss incident banner"
          style={{
            marginLeft: 'auto',
            background: 'none',
            border: 'none',
            color: '#64748b',
            cursor: 'pointer',
            padding: '0 0 0 6px',
            fontSize: '12px',
            lineHeight: 1,
            flexShrink: 0,
          }}
        >
          ✕
        </button>
      )}
    </div>
  );
};

export default IncidentBanner;
