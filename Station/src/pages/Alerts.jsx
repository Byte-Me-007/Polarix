import React, { useState, useMemo, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useStationTelemetry } from '../hooks/useStationTelemetry';
import { AlertSummaryCards } from '../components/alerts/AlertSummaryCards';
import { AlertFilterBar } from '../components/alerts/AlertFilterBar';
import { AlertList } from '../components/alerts/AlertList';
import { AlertHistory } from '../components/alerts/AlertHistory';
import { DemoMode } from '../components/DemoMode';
import { StationSelector } from '../components/StationSelector';

/**
 * Alerts Page
 * Central mission-control console for Antarctic Station alert and incident management.
 * Fully synchronized with Dashboard, Digital Twin, and Demo Mode.
 */
export const Alerts = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    activeStation,
    setActiveStation,
    config,
    allAlerts,
    acknowledgeAlert
  } = useStationTelemetry();

  const [activeSeverityFilter, setActiveSeverityFilter] = useState(() => location.state?.severityFilter || 'ALL');
  const [selectedZone, setSelectedZone] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (location.state?.severityFilter) {
      setActiveSeverityFilter(location.state.severityFilter);
    }
  }, [location.state]);

  // Total active (unacknowledged) alerts for header & summary
  const activeCount = useMemo(() => {
    return allAlerts.filter((a) => !a.acknowledged).length;
  }, [allAlerts]);

  // Acknowledged alerts for history audit table
  const historyAlerts = useMemo(() => {
    return allAlerts.filter((a) => a.acknowledged);
  }, [allAlerts]);

  // Filtered active alerts
  const filteredActiveAlerts = useMemo(() => {
    return allAlerts.filter((alert) => {
      // If user selected ACKNOWLEDGED filter, only show acknowledged
      if (activeSeverityFilter === 'ACKNOWLEDGED') {
        if (!alert.acknowledged) return false;
      } else {
        // By default or for severity filters, primary list shows unacknowledged
        if (alert.acknowledged && activeSeverityFilter !== 'ALL') return false;
      }

      // Severity matching
      if (activeSeverityFilter !== 'ALL' && activeSeverityFilter !== 'ACKNOWLEDGED') {
        if ((alert.severity || '').toUpperCase() !== activeSeverityFilter) return false;
      }

      // Zone matching
      if (selectedZone !== 'ALL') {
        const zoneStr = (alert.zone || '').toUpperCase();
        const targetZone = selectedZone.toUpperCase();
        if (!zoneStr.includes(targetZone) && !targetZone.includes(zoneStr)) return false;
      }

      // Search matching (sensor ID, title, message)
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const sensor = (alert.sensor_id || alert.sensorId || '').toLowerCase();
        const title = (alert.title || '').toLowerCase();
        const msg = (alert.message || '').toLowerCase();
        const zone = (alert.zone || '').toLowerCase();
        if (
          !sensor.includes(query) &&
          !title.includes(query) &&
          !msg.includes(query) &&
          !zone.includes(query)
        ) {
          return false;
        }
      }

      return true;
    });
  }, [allAlerts, activeSeverityFilter, selectedZone, searchQuery]);

  // Deep locate into 3D Digital Twin — passes zone, mode, and sensor focus
  const handleLocateInTwin = (alert) => {
    const alertStation = alert.station_id || alert.station;
    if (alertStation && alertStation !== activeStation) {
      setActiveStation(alertStation);
    }
    navigate('/digital-twin', {
      state: {
        locateSensorId: alert.sensor_id || alert.sensorId,
        focusZone: alert.zone || null,
        twinMode: 'XRAY'
      }
    });
  };


  const stationName = config?.displayName || `${activeStation} RESEARCH STATION`;
  const stationShort = config?.shortCode || activeStation;

  return (
    <main className="main-viewport alerts-page-container">
      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 1. OPERATIONAL PAGE HEADER                                      */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <section className="alerts-header-bar" aria-label="Alerts & Incidents Header">
        <div className="alerts-title-group">
          <h1>ALERTS & INCIDENTS</h1>
          <p className="alerts-subtitle">
            ACTIVE STATION EVENTS / REAL-TIME MONITORING
          </p>
        </div>

        <div className="alerts-header-right">
          <StationSelector />

          <div className="alerts-station-badge">
            <span className="station-name-tag">
              {stationShort} // {stationName}
            </span>
            <span className="online-indicator">
              <span className="status-dot-sm live" />
              ONLINE
            </span>
          </div>

          <div className="active-alerts-counter-pill">
            <span className="counter-label">ACTIVE ALERTS</span>
            <span className="counter-val">{String(activeCount).padStart(2, '0')}</span>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 2. SUMMARY STRIP (Counters for Critical, Warning, Offline, Ack) */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <section className="alerts-summary-section">
        <AlertSummaryCards
          alerts={allAlerts}
          activeFilter={activeSeverityFilter}
          onSelectFilter={(filterKey) => setActiveSeverityFilter(filterKey)}
        />
      </section>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 3. MULTI-DIMENSIONAL FILTER BAR                                 */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <section className="alerts-filter-section">
        <AlertFilterBar
          activeSeverity={activeSeverityFilter}
          onSelectSeverity={(sev) => setActiveSeverityFilter(sev)}
          selectedZone={selectedZone}
          onSelectZone={(z) => setSelectedZone(z)}
          searchQuery={searchQuery}
          onSearchChange={(q) => setSearchQuery(q)}
        />
      </section>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 4. PRIMARY OPERATIONAL ALERT FEED                               */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <section className="alerts-feed-section">
        <div className="alerts-feed-header">
          <h2 className="feed-title">
            {activeSeverityFilter === 'ACKNOWLEDGED' ? 'ACKNOWLEDGED INCIDENTS' : 'ACTIVE ALARM QUEUE'}
          </h2>
          <span className="feed-count">
            SHOWING {filteredActiveAlerts.length} {filteredActiveAlerts.length === 1 ? 'EVENT' : 'EVENTS'}
          </span>
        </div>

        <AlertList
          alerts={filteredActiveAlerts}
          onAcknowledge={acknowledgeAlert}
          onLocate={handleLocateInTwin}
        />
      </section>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 5. AUDITED ALERT HISTORY (Acknowledged / Resolved)              */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <section className="alerts-history-wrapper">
        <AlertHistory
          historyAlerts={historyAlerts}
          onLocate={handleLocateInTwin}
        />
      </section>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 6. DEMONSTRATION & SIMULATION ENVIRONMENT DOCK                  */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <section style={{ marginTop: '1.25rem' }}>
        <DemoMode />
      </section>
    </main>
  );
};

export default Alerts;
