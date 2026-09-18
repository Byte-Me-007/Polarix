/**
 * IncidentSummaryPanel.jsx
 *
 * Compact HTML overlay dock showing the full Cause → Impact chain for the
 * active operational incident.
 *
 * Design principles:
 *  - Maximum ~280px wide — the 3D station remains the hero
 *  - Positioned bottom-left of the canvas (does not overlap sensor/asset panels)
 *  - All displayed values derived from the incidentGraph (which comes from real state)
 *  - Shows DATA UNAVAILABLE where state doesn't support a field
 *  - Clickable assets → focus camera + asset inspection
 *  - Clickable sensors → open SensorDetailsPanel
 *  - "VIEW ALERT" → navigate to alerts page (uses existing navigation)
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

// ─────────────────────────────────────────────────────────────────────────────
// Severity color palette
// ─────────────────────────────────────────────────────────────────────────────

const SEV = {
  CRITICAL: { color: '#e53e3e', bg: 'rgba(181,56,43,0.16)', border: 'rgba(181,56,43,0.4)' },
  WARNING:  { color: '#d97706', bg: 'rgba(217,119,6,0.14)', border: 'rgba(217,119,6,0.38)' },
  INFO:     { color: '#94a3b8', bg: 'rgba(100,116,132,0.12)', border: 'rgba(100,116,132,0.3)' },
};

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

const SectionLabel = ({ children }) => (
  <div style={{
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: '7px',
    fontWeight: 800,
    letterSpacing: '0.14em',
    color: '#475569',
    textTransform: 'uppercase',
    marginBottom: '3px',
    marginTop: '8px',
  }}>
    {children}
  </div>
);

const SectionValue = ({ children, style }) => (
  <div style={{
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: '9px',
    fontWeight: 600,
    color: '#c8d0dc',
    lineHeight: 1.4,
    ...style,
  }}>
    {children}
  </div>
);

const AssetChip = ({ label, sensorId, onClick, onSensorClick }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginTop: '3px' }}>
    <button
      type="button"
      onClick={onClick}
      style={{
        background: 'rgba(182,90,31,0.12)',
        border: '1px solid rgba(182,90,31,0.35)',
        borderRadius: '3px',
        padding: '2px 7px',
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: '8px',
        fontWeight: 700,
        color: '#b65a1f',
        cursor: 'pointer',
        letterSpacing: '0.05em',
        transition: 'background 0.15s',
      }}
      onMouseEnter={e => e.currentTarget.style.background = 'rgba(182,90,31,0.22)'}
      onMouseLeave={e => e.currentTarget.style.background = 'rgba(182,90,31,0.12)'}
    >
      {label}
    </button>
    {sensorId && (
      <button
        type="button"
        onClick={onSensorClick}
        title={`Open sensor ${sensorId}`}
        style={{
          background: 'rgba(100,116,132,0.1)',
          border: '1px solid rgba(100,116,132,0.28)',
          borderRadius: '3px',
          padding: '2px 6px',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '7.5px',
          fontWeight: 600,
          color: '#64748b',
          cursor: 'pointer',
          letterSpacing: '0.04em',
          transition: 'background 0.15s',
        }}
        onMouseEnter={e => e.currentTarget.style.background = 'rgba(100,116,132,0.2)'}
        onMouseLeave={e => e.currentTarget.style.background = 'rgba(100,116,132,0.1)'}
      >
        {sensorId}
      </button>
    )}
  </div>
);

const Divider = () => (
  <div style={{
    height: '1px',
    background: 'rgba(255,255,255,0.06)',
    margin: '8px 0',
  }} />
);

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────

export const IncidentSummaryPanel = ({
  incidentGraph,
  onSelectNode,
  onSelectSensor,
  isCompact = false,    // compact when sensor/asset panel is open
}) => {
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  if (!incidentGraph?.isActive) return null;

  const {
    scenarioLabel,
    scenarioBadge,
    scenarioSeverity,
    causeLabel,
    systemResponseLabel,
    impactLabel,
    nodes,
    primaryAlert,
  } = incidentGraph;

  const sev = scenarioSeverity || 'WARNING';
  const sevStyle = SEV[sev] || SEV.WARNING;

  // Affected asset nodes (those with an associated asset)
  const assetNodes = (nodes || []).filter(n => n.asset);

  const handleAlertClick = () => {
    navigate('/alerts');
  };

  const handleNodeClick = (node) => {
    if (onSelectNode) onSelectNode(node);
  };

  const handleSensorClick = (sensorId) => {
    if (onSelectSensor) onSelectSensor(sensorId);
  };

  return (
    <div
      style={{
        position: 'absolute',
        bottom: '48px',
        left: '10px',
        zIndex: 85,
        width: isCompact ? '180px' : '268px',
        background: 'rgba(12, 15, 21, 0.97)',
        border: `1px solid ${sevStyle.border}`,
        borderRadius: '6px',
        boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
        backdropFilter: 'blur(6px)',
        pointerEvents: 'auto',
        transition: 'width 0.2s ease',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        onClick={() => setCollapsed(v => !v)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '7px 10px',
          cursor: 'pointer',
          borderBottom: collapsed ? 'none' : `1px solid rgba(255,255,255,0.06)`,
          userSelect: 'none',
        }}
      >
        {/* Severity dot */}
        <span style={{
          width: '7px', height: '7px', borderRadius: '50%',
          background: sevStyle.color, flexShrink: 0,
          boxShadow: `0 0 5px ${sevStyle.color}66`,
        }} />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '9.5px',
            fontWeight: 800,
            letterSpacing: '0.07em',
            color: '#f0ece4',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {scenarioLabel}
          </div>
          {!isCompact && (
            <div style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '7px',
              color: sevStyle.color,
              fontWeight: 700,
              letterSpacing: '0.1em',
              marginTop: '1px',
            }}>
              {sev} · {scenarioBadge}
            </div>
          )}
        </div>

        {/* Collapse toggle */}
        <span style={{
          color: '#475569',
          fontSize: '10px',
          flexShrink: 0,
          transform: collapsed ? 'rotate(-90deg)' : 'none',
          transition: 'transform 0.15s',
        }}>
          ▼
        </span>
      </div>

      {/* Body — collapsible */}
      {!collapsed && !isCompact && (
        <div style={{ padding: '2px 12px 10px' }}>

          {/* CAUSE */}
          <SectionLabel>CAUSE</SectionLabel>
          <SectionValue>
            {causeLabel || 'DATA UNAVAILABLE'}
          </SectionValue>

          <Divider />

          {/* SYSTEM RESPONSE */}
          <SectionLabel>SYSTEM RESPONSE</SectionLabel>
          <SectionValue>
            {systemResponseLabel || 'DATA UNAVAILABLE'}
          </SectionValue>

          <Divider />

          {/* IMPACT */}
          <SectionLabel>IMPACT</SectionLabel>
          <SectionValue>
            {impactLabel || 'DATA UNAVAILABLE'}
          </SectionValue>

          {/* AFFECTED ASSETS */}
          {assetNodes.length > 0 && (
            <>
              <Divider />
              <SectionLabel>AFFECTED ASSETS</SectionLabel>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
                {assetNodes.map(node => (
                  <AssetChip
                    key={node.id}
                    label={node.asset?.label || node.id}
                    sensorId={node.sensorId}
                    onClick={() => handleNodeClick(node)}
                    onSensorClick={() => handleSensorClick(node.sensorId)}
                  />
                ))}
              </div>
            </>
          )}

          {/* RELATED ALERT */}
          {primaryAlert && (
            <>
              <Divider />
              <SectionLabel>RELATED ALERT</SectionLabel>
              <div style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '6px',
                background: 'rgba(181,56,43,0.08)',
                border: '1px solid rgba(181,56,43,0.25)',
                borderRadius: '4px',
                padding: '5px 8px',
                marginBottom: '4px',
              }}>
                <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#e53e3e', flexShrink: 0, marginTop: '2px' }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '8px',
                    fontWeight: 700,
                    color: '#e53e3e',
                    letterSpacing: '0.04em',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}>
                    {primaryAlert.severity} ALERT
                  </div>
                  <div style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '7.5px',
                    color: '#94a3b8',
                    marginTop: '1px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {primaryAlert.title}
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={handleAlertClick}
                style={{
                  display: 'block',
                  width: '100%',
                  background: 'rgba(181,56,43,0.12)',
                  border: '1px solid rgba(181,56,43,0.35)',
                  borderRadius: '3px',
                  padding: '4px 8px',
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: '8px',
                  fontWeight: 700,
                  color: '#e53e3e',
                  cursor: 'pointer',
                  letterSpacing: '0.08em',
                  textAlign: 'center',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(181,56,43,0.22)'}
                onMouseLeave={e => e.currentTarget.style.background = 'rgba(181,56,43,0.12)'}
              >
                VIEW ALERT →
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default IncidentSummaryPanel;
