import React from 'react';
import { useStationTelemetry } from '../hooks/useStationTelemetry';
import { HealthScore } from '../components/HealthScore';
import { MetricCard } from '../components/MetricCard';
import { EnvironmentSummary } from '../components/EnvironmentSummary';
import { AlertSummary } from '../components/AlertSummary';
import { QuickActions } from '../components/QuickActions';
import { DemoMode } from '../components/DemoMode';

export const Dashboard = () => {
  const { config, telemetry } = useStationTelemetry();
  const operationalStatus = telemetry.healthStatus === 'HEALTHY' || telemetry.healthStatus === 'OPTIMAL'
    ? 'OPERATIONAL' 
    : telemetry.healthStatus;

  const getOperationalClass = (status) => {
    if (status === 'HEALTHY' || status === 'OPERATIONAL' || status === 'OPTIMAL') return '';
    if (status === 'CRITICAL') return 'critical';
    return 'degraded';
  };

  const stationDisplayName = config.displayName 
    ? config.displayName.toUpperCase() 
    : `${config.stationId || 'MAITRI'} RESEARCH STATION`;

  const stationCode = config.shortCode || config.id || 'MTR';
  const stationAltitude = config.altitude || config.elevation || '117 m a.s.l.';
  const expeditionText = config.expedition || '45th Indian Scientific Expedition to Antarctica';
  const personnelCount = config.personnelOnsite || 24;

  return (
    <main className="main-viewport">
      {/* 6. STATION IDENTITY HEADER (Configuration-Driven, Large, Editorial) */}
      <section className="station-editorial-header" aria-label="Station Identity">
        <div className="station-title-block">
          <h1>{stationDisplayName}</h1>
          <div className="station-meta-strip">
            <span className="meta-pill">{stationCode} / ANTARCTICA</span>
            <span className="meta-coords">{config.coordinates}</span>
            <span>•</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--polaris-text-muted)' }}>
              {stationAltitude}
            </span>
            <span>•</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--polaris-text-secondary)' }}>
              {expeditionText} // {personnelCount} ONSITE
            </span>
          </div>
        </div>

        {/* Operational Indicator */}
        <div className={`header-operational-badge ${getOperationalClass(operationalStatus)}`}>
          <span className="status-dot-sm" style={{ background: 'currentColor' }} />
          <span>{operationalStatus}</span>
        </div>
      </section>

      {/* 7 & 8. EXECUTIVE TELEMETRY: STATION READINESS + DIFFERENTIATED SYSTEMS GRID */}
      <section className="executive-telemetry-row" aria-label="Station Readiness and Systems Telemetry">
        <HealthScore />
        <MetricCard />
      </section>

      {/* 9. ENVIRONMENTAL TELEMETRY: MAIN ANALYTICAL OBSERVATION INSTRUMENT */}
      <EnvironmentSummary />

      {/* 10 & 11. ACTIVE EVENTS TIMELINE & OPERATIONAL COMMANDS */}
      <section className="lower-operations-grid" aria-label="Events Timeline and Commands">
        <AlertSummary />
        <QuickActions />
      </section>

      {/* 12. SIMULATION CONTROL DOCK */}
      <DemoMode />
    </main>
  );
};

export default Dashboard;
