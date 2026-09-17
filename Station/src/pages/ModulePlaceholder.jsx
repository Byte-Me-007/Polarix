import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { useStationTelemetry } from '../hooks/useStationTelemetry';

const moduleConfigs = {
  '/digital-twin': {
    title: 'STATION 3D DIGITAL TWIN',
    subtitle: 'High-fidelity structural model, thermal heat-loss zones, and BIM sensor telemetry.',
    code: 'MOD // DT-01',
    phase: 'Phase 2 Implementation: Three.js / React Three Fiber asset pipeline.'
  },
  '/alerts': {
    title: 'STATION ALARMS & DIAGNOSTIC LOG',
    subtitle: 'Comprehensive event register, telemetry fault detection, and engineer acknowledgment protocol.',
    code: 'MOD // AL-02',
    phase: 'Operational Event Review Console'
  },
  '/energy': {
    title: 'MICROGRID ENERGY DISPATCH & FORECAST',
    subtitle: 'Bifacial solar array irradiance, wind turbine pitch curves, generator fuel burn, and battery storage.',
    code: 'MOD // EN-03',
    phase: 'Energy forecasting & dispatch analytics under active development.'
  },
  '/logistics': {
    title: 'POLAR LOGISTICS & RESUPPLY SCHEDULING',
    subtitle: 'Diesel fuel reserves, rations, scientific spares inventory, and expedition resupply vessel tracking.',
    code: 'MOD // LG-04',
    phase: 'Supply chain tracking system scheduled for expedition season 2026-27.'
  },
  '/sensors': {
    title: 'IOT SENSOR ARRAY TOPOLOGY',
    subtitle: 'Wireless mesh sensor nodes, mast anemometers, structural strain gauges, and RF signal strength.',
    code: 'MOD // SN-05',
    phase: 'Sub-station sensor telemetry topology in progress.'
  },
  '/events': {
    title: 'EXPEDITION LOG & OPERATIONS TIMELINE',
    subtitle: 'Scientific schedules, weather windows, daily maintenance tasks, and communication logs.',
    code: 'MOD // EV-06',
    phase: 'Expedition mission timeline and scheduler under development.'
  },
  '/settings': {
    title: 'MISSION CONTROL SYSTEM CONFIGURATION',
    subtitle: 'GSAT transceiver frequencies, alerting thresholds, MQTT endpoint setup, and cryptographic credentials.',
    code: 'MOD // CF-07',
    phase: 'Transceiver configuration console under development.'
  }
};

export const ModulePlaceholder = () => {
  const location = useLocation();
  const { alerts, acknowledgeAlert, config } = useStationTelemetry();
  const currentMod = moduleConfigs[location.pathname] || {
    title: 'ANTARCTIC MISSION MODULE',
    subtitle: 'Scientific operations module.',
    code: 'MOD // SYS',
    phase: 'Module under development.'
  };

  const isAlertsPage = location.pathname === '/alerts';

  return (
    <main className="main-viewport">
      <div style={{ marginBottom: '1.5rem' }}>
        <Link to="/" className="polaris-return-link">
          ← RETURN TO POLARIS MISSION DASHBOARD
        </Link>
      </div>

      {isAlertsPage ? (
        <div style={{ background: 'var(--polaris-bg-surface)', border: '1px solid var(--polaris-border)', borderRadius: 'var(--radius-sm)', padding: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.75rem', borderBottom: '1px solid var(--polaris-border-subtle)', paddingBottom: '1rem' }}>
            <div>
              <span className="polaris-module-badge">{currentMod.code}</span>
              <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--polaris-text-primary)', marginTop: '0.25rem' }}>
                {config.name} STATION ALARMS & DIAGNOSTICS
              </h2>
              <p style={{ fontSize: '0.8125rem', color: 'var(--polaris-text-secondary)', marginTop: '0.25rem' }}>
                Active anomaly notifications and life-support subsystem warnings
              </p>
            </div>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 600, color: 'var(--polaris-copper)', background: 'var(--polaris-copper-subtle)', padding: '0.2rem 0.6rem', border: '1px solid var(--polaris-copper-border)', borderRadius: 'var(--radius-xs)' }}>
              {alerts.length} ALARMS LOGGED
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {alerts.map((alert) => (
              <div 
                key={alert.id} 
                style={{
                  background: 'var(--polaris-bg-elevated)',
                  border: '1px solid var(--polaris-border)',
                  borderLeft: `4px solid ${alert.severity === 'CRITICAL' ? 'var(--status-critical)' : alert.severity === 'WARNING' ? 'var(--status-warning)' : 'var(--polaris-sage)'}`,
                  borderRadius: 'var(--radius-xs)',
                  padding: '1rem 1.25rem'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <span style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.6875rem',
                      fontWeight: 700,
                      color: alert.severity === 'CRITICAL' ? 'var(--status-critical)' : alert.severity === 'WARNING' ? 'var(--status-warning)' : 'var(--polaris-sage)'
                    }}>
                      ● {alert.severity}
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--polaris-text-muted)' }}>
                      // SUBSYSTEM: {alert.subsystem}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--polaris-text-muted)' }}>
                      {alert.timestamp}
                    </span>
                    <button
                      type="button"
                      onClick={() => acknowledgeAlert(alert.id)}
                      disabled={alert.acknowledged}
                      style={{
                        background: alert.acknowledged ? 'transparent' : 'var(--polaris-bg-surface)',
                        border: '1px solid',
                        borderColor: alert.acknowledged ? 'var(--polaris-border)' : 'var(--polaris-copper)',
                        color: alert.acknowledged ? 'var(--polaris-text-muted)' : 'var(--polaris-copper)',
                        padding: '0.2rem 0.65rem',
                        borderRadius: 'var(--radius-xs)',
                        fontSize: '0.6875rem',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 600,
                        cursor: alert.acknowledged ? 'default' : 'pointer'
                      }}
                    >
                      {alert.acknowledged ? 'ACKNOWLEDGED' : 'ACKNOWLEDGE'}
                    </button>
                  </div>
                </div>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--polaris-text-primary)', marginBottom: '0.25rem' }}>
                  {alert.title}
                </div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--polaris-text-secondary)', lineHeight: 1.45 }}>
                  {alert.message}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="polaris-module-view">
          <span className="polaris-module-badge">{currentMod.code}</span>
          <h2 style={{ fontSize: '1.65rem', fontWeight: 800, color: 'var(--polaris-text-primary)', marginBottom: '0.5rem' }}>
            {currentMod.title}
          </h2>
          <p style={{ fontSize: '0.875rem', color: 'var(--polaris-text-secondary)', maxWidth: '580px', margin: '0 auto 1.5rem', lineHeight: 1.5 }}>
            {currentMod.subtitle}
          </p>

          <div style={{
            display: 'inline-block',
            background: 'var(--polaris-bg-subtle)',
            border: '1px dashed var(--polaris-border-strong)',
            padding: '0.75rem 1.5rem',
            borderRadius: 'var(--radius-xs)',
            fontSize: '0.75rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--polaris-text-muted)',
            marginBottom: '2rem'
          }}>
            {currentMod.phase}
          </div>

          <div>
            <Link 
              to="/" 
              style={{
                display: 'inline-block',
                background: 'var(--polaris-copper)',
                color: '#ffffff',
                padding: '0.6rem 1.25rem',
                borderRadius: 'var(--radius-xs)',
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                letterSpacing: '0.04em',
                textDecoration: 'none'
              }}
            >
              RETURN TO DASHBOARD
            </Link>
          </div>
        </div>
      )}
    </main>
  );
};

export default ModulePlaceholder;
