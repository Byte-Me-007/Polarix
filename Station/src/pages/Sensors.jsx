import React, { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStationTelemetry } from '../hooks/useStationTelemetry';

export const Sensors = () => {
  const navigate = useNavigate();
  const { config, sensors: rawSensors } = useStationTelemetry();

  // Filters
  const [selectedDomain, setSelectedDomain] = useState('ALL');
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  
  // Selected sensor for detail modal
  const [activeSensor, setActiveSensor] = useState(null);

  // Close modal on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setActiveSensor(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const stationSensors = useMemo(() => {
    return rawSensors || config.sensors || [];
  }, [rawSensors, config]);

  // Dynamic summary counts
  const summaryCounts = useMemo(() => {
    const total = stationSensors.length;
    let normal = 0;
    let warning = 0;
    let critical = 0;
    let offline = 0;

    stationSensors.forEach((s) => {
      const st = s.status?.toUpperCase();
      if (st === 'NORMAL') normal++;
      else if (st === 'WARNING') warning++;
      else if (st === 'CRITICAL') critical++;
      else if (st === 'OFFLINE') offline++;
    });

    return { total, normal, warning, critical, offline };
  }, [stationSensors]);

  // Available domain & status options
  const domains = ['ALL', 'ENVIRONMENT', 'STRUCTURE', 'ENERGY', 'LOGISTICS'];
  const statuses = ['ALL', 'NORMAL', 'WARNING', 'CRITICAL', 'OFFLINE', 'UNKNOWN'];

  // Filtered sensor list (combining domain and status filters)
  const filteredSensors = useMemo(() => {
    return stationSensors.filter((sensor) => {
      const matchDomain = selectedDomain === 'ALL' || sensor.domain?.toUpperCase() === selectedDomain;
      const matchStatus = selectedStatus === 'ALL' || sensor.status?.toUpperCase() === selectedStatus;
      return matchDomain && matchStatus;
    });
  }, [stationSensors, selectedDomain, selectedStatus]);

  const getStatusClass = (status) => {
    switch (status?.toUpperCase()) {
      case 'NORMAL': return 'normal';
      case 'WARNING': return 'warning';
      case 'CRITICAL': return 'critical';
      case 'OFFLINE': return 'offline';
      default: return 'unknown';
    }
  };

  const stationDisplay = config.displayName || `${config.stationId || 'MAITRI'} Research Station`;
  const stationCode = config.shortCode || config.id || 'MTR';

  return (
    <main className="main-viewport sensors-page-container">
      {/* 1. PAGE HEADER */}
      <section className="sensors-header-bar" aria-label="Sensor Monitoring Header">
        <div className="sensors-title-group">
          <h1>SENSOR MONITORING</h1>
          <p className="sensors-subtitle">
            Station sensor registry and live telemetry status
          </p>
        </div>

        <div className="sensors-station-stamp">
          <span className="station-badge-clean">
            {stationDisplay.toUpperCase()} / {stationCode} • {stationSensors.length} SENSORS
          </span>
          <span className="simulation-data-tag">
            DEMO TELEMETRY
          </span>
        </div>
      </section>

      {/* 2. SUMMARY STRIP (Dynamically Calculated) */}
      <section className="sensors-summary-strip" aria-label="Sensor Subsystem Status Summary">
        <div className="summary-stat-cell">
          <span className="summary-stat-label">TOTAL SENSORS</span>
          <span className="summary-stat-value">{String(summaryCounts.total).padStart(2, '0')}</span>
        </div>

        <div className="summary-stat-cell">
          <span className="summary-stat-label">
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--status-normal)' }} />
            NORMAL
          </span>
          <span className="summary-stat-value normal">{String(summaryCounts.normal).padStart(2, '0')}</span>
        </div>

        <div className="summary-stat-cell">
          <span className="summary-stat-label">
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--status-warning)' }} />
            WARNING
          </span>
          <span className="summary-stat-value warning">{String(summaryCounts.warning).padStart(2, '0')}</span>
        </div>

        <div className="summary-stat-cell">
          <span className="summary-stat-label">
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--status-critical)' }} />
            CRITICAL
          </span>
          <span className="summary-stat-value critical">{String(summaryCounts.critical).padStart(2, '0')}</span>
        </div>

        <div className="summary-stat-cell">
          <span className="summary-stat-label">
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--status-offline)' }} />
            OFFLINE
          </span>
          <span className="summary-stat-value offline">{String(summaryCounts.offline).padStart(2, '0')}</span>
        </div>
      </section>

      {/* 3 & 4. DOMAIN & STATUS FILTERS (Working together) */}
      <section className="sensors-filter-bar" aria-label="Sensor Filtering Controls">
        {/* Domain Filter */}
        <div className="filter-group-wrap" role="group" aria-label="Filter by Domain">
          <span className="filter-group-label">DOMAIN:</span>
          {domains.map((dom) => (
            <button
              key={dom}
              type="button"
              className={`filter-pill-button ${selectedDomain === dom ? 'active' : ''}`}
              onClick={() => setSelectedDomain(dom)}
              aria-pressed={selectedDomain === dom}
            >
              {dom}
            </button>
          ))}
        </div>

        {/* Status Filter */}
        <div className="filter-group-wrap" role="group" aria-label="Filter by Status">
          <span className="filter-group-label">STATUS:</span>
          {statuses.map((st) => (
            <button
              key={st}
              type="button"
              className={`filter-pill-button ${selectedStatus === st ? 'active' : ''}`}
              onClick={() => setSelectedStatus(st)}
              aria-pressed={selectedStatus === st}
            >
              {st}
            </button>
          ))}
        </div>
      </section>

      {/* 5. SENSOR TABLE / REGISTRY */}
      <section className="sensor-table-container" aria-label="Sensor Table Registry">
        <div className="sensor-table-header-info">
          <span>SHOWING {filteredSensors.length} OF {stationSensors.length} REGISTERED TRANSDUCERS</span>
          <span>CLICK ANY SENSOR ROW FOR DETAILED INSTRUMENT SPECIFICATIONS</span>
        </div>

        {/* Desktop & Tablet Table */}
        <div className="sensor-table-scroll">
          <table className="sensor-table">
            <thead>
              <tr>
                <th scope="col">STATUS</th>
                <th scope="col">SENSOR</th>
                <th scope="col">DOMAIN</th>
                <th scope="col">VALUE</th>
                <th scope="col">UNIT</th>
                <th scope="col">QUALITY</th>
                <th scope="col">LAST UPDATE</th>
                <th scope="col">POSITION</th>
              </tr>
            </thead>
            <tbody>
              {filteredSensors.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '3rem', color: 'var(--polaris-text-muted)' }}>
                    No sensors match the current domain "{selectedDomain}" and status "{selectedStatus}" filters.
                  </td>
                </tr>
              ) : (
                filteredSensors.map((sensor) => {
                  const statusCls = getStatusClass(sensor.status);
                  return (
                    <tr
                      key={sensor.id}
                      className="sensor-table-row"
                      onClick={() => setActiveSensor(sensor)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setActiveSensor(sensor);
                        }
                      }}
                      tabIndex={0}
                      role="button"
                      aria-label={`View details for ${sensor.name}`}
                    >
                      {/* STATUS */}
                      <td>
                        <span className={`sensor-status-indicator ${statusCls}`}>
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'currentColor' }} />
                          <span>{sensor.status?.toUpperCase() || 'NORMAL'}</span>
                        </span>
                      </td>

                      {/* SENSOR */}
                      <td>
                        <div className="sensor-name-col">
                          <span className="sensor-primary-name">{sensor.name}</span>
                          <span className="sensor-id-sub">{sensor.id}</span>
                        </div>
                      </td>

                      {/* DOMAIN */}
                      <td>
                        <span className="sensor-domain-badge">{sensor.domain}</span>
                      </td>

                      {/* VALUE */}
                      <td>
                        <span className="sensor-tabular-val">{sensor.value}</span>
                      </td>

                      {/* UNIT */}
                      <td>
                        <span className="sensor-unit-tag">{sensor.unit}</span>
                      </td>

                      {/* QUALITY */}
                      <td>
                        <span className="sensor-quality-tag">{sensor.quality || 'GOOD'}</span>
                      </td>

                      {/* LAST UPDATE */}
                      <td>
                        <span className="sensor-time-tag">{sensor.lastUpdate || '19:28:09 UTC'}</span>
                      </td>

                      {/* POSITION */}
                      <td>
                        <span className="sensor-coords-tag">
                          X {sensor.x} / Y {sensor.y} / Z {sensor.z}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* 9. Mobile Stacked Cards (<768px) */}
        <div className="sensor-mobile-cards">
          {filteredSensors.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--polaris-text-muted)' }}>
              No sensors match current filter parameters.
            </div>
          ) : (
            filteredSensors.map((sensor) => {
              const statusCls = getStatusClass(sensor.status);
              return (
                <div
                  key={sensor.id}
                  className="sensor-card-mobile"
                  onClick={() => setActiveSensor(sensor)}
                  tabIndex={0}
                  role="button"
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                    <div>
                      <div className="sensor-primary-name">{sensor.name}</div>
                      <div className="sensor-id-sub">{sensor.id}</div>
                    </div>
                    <span className={`sensor-status-indicator ${statusCls}`}>
                      <span>{sensor.status}</span>
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', borderTop: '1px solid var(--polaris-border-subtle)', paddingTop: '0.5rem' }}>
                    <div>
                      <span className="sensor-tabular-val" style={{ fontSize: '1.4rem' }}>{sensor.value}</span>
                      <span className="sensor-unit-tag" style={{ marginLeft: '0.2rem' }}>{sensor.unit}</span>
                    </div>
                    <span className="sensor-domain-badge">{sensor.domain}</span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6875rem', color: 'var(--polaris-text-muted)', fontFamily: 'var(--font-mono)' }}>
                    <span>X {sensor.x} / Y {sensor.y} / Z {sensor.z}</span>
                    <span>{sensor.lastUpdate}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </section>

      {/* 7 & 8. SENSOR DETAIL INTERACTION (Panel / Modal) */}
      {activeSensor && (
        <div 
          className="sensor-modal-backdrop" 
          onClick={() => setActiveSensor(null)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="sensor-detail-title"
        >
          <div className="sensor-modal-content" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="sensor-modal-header">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                  <span className="sensor-domain-badge">{activeSensor.domain}</span>
                  <span className={`sensor-status-indicator ${getStatusClass(activeSensor.status)}`}>
                    ● {activeSensor.status}
                  </span>
                </div>
                <h3 id="sensor-detail-title" style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--polaris-text-primary)' }}>
                  {activeSensor.name}
                </h3>
                <span className="sensor-id-sub">STATION ASSET ID: {activeSensor.id}</span>
              </div>

              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setActiveSensor(null)}
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="sensor-modal-body">
              {/* Hero Reading Banner */}
              <div className="sensor-hero-telemetry-banner">
                <div>
                  <div className="spec-label">LIVE TRANSDUCER VALUE</div>
                  <div className="sensor-hero-reading">
                    {activeSensor.value}
                    <span className="unit">{activeSensor.unit}</span>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="spec-label">DATA QUALITY</div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--status-normal)' }}>
                    {activeSensor.quality || 'GOOD'}
                  </span>
                </div>
              </div>

              {/* Specifications & Calibration Grid */}
              <div className="sensor-spec-grid">
                <div className="spec-item">
                  <span className="spec-label">SENSOR TYPE</span>
                  <span className="spec-value">{activeSensor.type || 'INSTRUMENT'}</span>
                </div>

                <div className="spec-item">
                  <span className="spec-label">DOMAIN CLUSTER</span>
                  <span className="spec-value">{activeSensor.domain}</span>
                </div>

                <div className="spec-item">
                  <span className="spec-label">SUBSYSTEM CRITICALITY</span>
                  <span className="spec-value">{activeSensor.criticality || 'HIGH'}</span>
                </div>

                <div className="spec-item">
                  <span className="spec-label">LAST TELEMETRY UPDATE</span>
                  <span className="spec-value">{activeSensor.lastUpdate || '19:28:09 UTC'}</span>
                </div>

                <div className="spec-item">
                  <span className="spec-label">MIN CALIBRATION LIMIT</span>
                  <span className="spec-value">{activeSensor.minValue ?? 'N/A'} {activeSensor.unit}</span>
                </div>

                <div className="spec-item">
                  <span className="spec-label">MAX CALIBRATION LIMIT</span>
                  <span className="spec-value">{activeSensor.maxValue ?? 'N/A'} {activeSensor.unit}</span>
                </div>

                <div className="spec-item" style={{ gridColumn: 'span 2' }}>
                  <span className="spec-label">SPATIAL COORDINATES (BIM / 3D STATION DATUM)</span>
                  <span className="spec-value" style={{ color: 'var(--polaris-copper)' }}>
                    X: {activeSensor.x} m &nbsp;|&nbsp; Y: {activeSensor.y} m &nbsp;|&nbsp; Z: {activeSensor.z} m
                  </span>
                </div>
              </div>
            </div>

            {/* Modal Footer with Digital Twin Action */}
            <div className="sensor-modal-footer">
              <span style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--polaris-text-muted)' }}>
                Inspect live spatial coordinate datum in 3D Digital Twin.
              </span>

              <button
                type="button"
                className="digital-twin-action-btn"
                onClick={() => navigate('/digital-twin')}
                style={{ cursor: 'pointer', opacity: 1, color: '#ffffff', background: 'var(--polaris-copper)', borderColor: 'var(--polaris-copper)' }}
                title="Navigate to 3D Digital Twin Viewport"
              >
                VIEW IN DIGITAL TWIN →
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
};

export default Sensors;
