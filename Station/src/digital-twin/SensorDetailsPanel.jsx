import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

/**
 * SensorDetailsPanel
 * Professional scientific right-side telemetry inspection panel.
 * Slides in from the right, keeping 3D station visible in background.
 * Converts to responsive bottom sheet on smaller screens.
 */
export const SensorDetailsPanel = ({ sensor, onClose }) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  if (!sensor) return null;

  const status = (sensor.status || 'UNKNOWN').toUpperCase();

  // Status color mapping adhering strictly to POLARIS design guidelines (NO cyan/blue)
  const getStatusTheme = (st) => {
    switch (st) {
      case 'NORMAL':
        return {
          color: '#3f6e4a',
          bg: 'rgba(63, 110, 74, 0.10)',
          border: 'rgba(63, 110, 74, 0.35)',
          badgeText: 'NORMAL',
          desc: 'NOMINAL TELEMETRY'
        };
      case 'WARNING':
        return {
          color: '#b26814',
          bg: 'rgba(178, 104, 20, 0.12)',
          border: 'rgba(178, 104, 20, 0.40)',
          badgeText: 'WARNING',
          desc: 'CAUTIONARY THRESHOLD'
        };
      case 'CRITICAL':
        return {
          color: '#b5382b',
          bg: 'rgba(181, 56, 43, 0.12)',
          border: 'rgba(181, 56, 43, 0.40)',
          badgeText: 'CRITICAL',
          desc: 'ACTIVE ALARM THRESHOLD'
        };
      case 'OFFLINE':
        return {
          color: '#5d6672',
          bg: 'rgba(93, 102, 114, 0.10)',
          border: 'rgba(93, 102, 114, 0.30)',
          badgeText: 'OFFLINE',
          desc: 'NO CARRIER SIGNAL'
        };
      default:
        return {
          color: '#727b87',
          bg: 'rgba(114, 123, 135, 0.10)',
          border: 'rgba(114, 123, 135, 0.30)',
          badgeText: 'UNKNOWN',
          desc: 'STATE INDETERMINATE'
        };
    }
  };

  const theme = getStatusTheme(status);

  // ECharts initialization for recent telemetry history
  useEffect(() => {
    if (!chartRef.current || !sensor.recentReadings || sensor.recentReadings.length === 0) {
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
      return;
    }

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, null, {
        renderer: 'canvas'
      });
    }

    const times = sensor.recentReadings.map((r) => r.time);
    const values = sensor.recentReadings.map((r) => r.value);

    const option = {
      backgroundColor: 'transparent',
      animationDuration: 400,
      grid: {
        top: 14,
        right: 14,
        bottom: 24,
        left: 36,
        containLabel: false
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#ffffff',
        borderColor: '#e5ded4',
        borderWidth: 1,
        padding: [4, 8],
        textStyle: {
          color: '#191c20',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11
        },
        formatter: (params) => {
          if (!params || !params[0]) return '';
          return `${params[0].name}: <strong>${params[0].value} ${sensor.unit}</strong>`;
        }
      },
      xAxis: {
        type: 'category',
        data: times,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#dcd5c9' } },
        axisTick: { show: false },
        axisLabel: {
          color: '#7c8594',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 10
        }
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitNumber: 3,
        splitLine: {
          lineStyle: {
            color: '#ede7dc',
            type: 'dashed'
          }
        },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: '#7c8594',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 10
        }
      },
      series: [
        {
          name: sensor.name,
          type: 'line',
          data: values,
          smooth: true,
          showSymbol: true,
          symbolSize: 4,
          itemStyle: {
            color: theme.color
          },
          lineStyle: {
            width: 2,
            color: theme.color
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: theme.color + '40' },
              { offset: 1, color: theme.color + '05' }
            ])
          }
        }
      ]
    };

    chartInstance.current.setOption(option);

    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
    };
  }, [sensor, theme.color]);

  // Format physical coordinates cleanly
  const posX = typeof sensor.x === 'number' ? sensor.x.toFixed(2) : '—';
  const posY = typeof sensor.y === 'number' ? sensor.y.toFixed(2) : '—';
  const posZ = typeof sensor.z === 'number' ? sensor.z.toFixed(2) : '—';

  return (
    <aside
      className="twin-detail-drawer"
      aria-label="3D Sensor Telemetry Inspection"
      onClick={(e) => e.stopPropagation()}
    >
      {/* ─────────────────────────────────────────────────────────────── */}
      {/* 1. PANEL HEADER                                                 */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <div className="twin-drawer-header">
        <div className="sensor-header-text">
          <span className="sensor-category-label">SENSOR</span>
          <h2 className="sensor-id-title">{sensor.id}</h2>
          <span className="sensor-zone-badge">{sensor.zone}</span>
        </div>

        <button
          type="button"
          className="twin-drawer-close-btn"
          onClick={onClose}
          aria-label="Close sensor inspector"
          title="Close sensor details (Esc)"
        >
          × CLOSE
        </button>
      </div>

      <div className="twin-drawer-body">
        {/* ───────────────────────────────────────────────────────────── */}
        {/* 2. LARGE STATUS INDICATOR                                     */}
        {/* ───────────────────────────────────────────────────────────── */}
        <div
          className="sensor-status-banner"
          style={{
            background: theme.bg,
            borderColor: theme.border,
            color: theme.color
          }}
        >
          <div className="status-dot-wrap">
            <span
              className="status-dot"
              style={{ background: theme.color }}
            />
          </div>
          <div className="status-text-wrap">
            <span className="status-title">{theme.badgeText}</span>
            <span className="status-desc">{theme.desc}</span>
          </div>
        </div>

        {/* ───────────────────────────────────────────────────────────── */}
        {/* 3. CURRENT READING (MAIN HERO VALUE)                          */}
        {/* ───────────────────────────────────────────────────────────── */}
        <div className="sensor-hero-card">
          <div className="hero-reading-row">
            <span className="hero-value">{sensor.value ?? '—'}</span>
            <span className="hero-unit">{sensor.unit || ''}</span>
          </div>
          <div className="hero-type-label">
            {sensor.type || sensor.domain || 'TRANSDUCER MEASUREMENT'}
          </div>
          <div className="hero-sensor-name">
            {sensor.name}
          </div>
        </div>

        {/* ───────────────────────────────────────────────────────────── */}
        {/* 4. SENSOR INFORMATION LIST                                    */}
        {/* ───────────────────────────────────────────────────────────── */}
        <div className="sensor-info-section">
          <div className="section-title">SENSOR INFORMATION</div>
          <dl className="sensor-data-table">
            <div className="data-row">
              <dt>SENSOR ID</dt>
              <dd className="mono-val">{sensor.id}</dd>
            </div>
            <div className="data-row">
              <dt>ZONE</dt>
              <dd className="mono-val">{sensor.zone}</dd>
            </div>
            <div className="data-row">
              <dt>STATUS</dt>
              <dd className="mono-val" style={{ color: theme.color, fontWeight: 700 }}>
                {status}
              </dd>
            </div>
            <div className="data-row">
              <dt>VALUE</dt>
              <dd className="mono-val">{sensor.value ?? '—'}</dd>
            </div>
            <div className="data-row">
              <dt>UNIT</dt>
              <dd className="mono-val">{sensor.unit || '—'}</dd>
            </div>
            <div className="data-row">
              <dt>QUALITY</dt>
              <dd className="mono-val">{sensor.quality || 'GOOD'}</dd>
            </div>
            <div className="data-row">
              <dt>SOURCE</dt>
              <dd className="mono-val">{sensor.source || 'SIMULATION'}</dd>
            </div>
            <div className="data-row">
              <dt>TIMESTAMP</dt>
              <dd className="mono-val">{sensor.lastUpdate || '2026-09-18 01:42:18 UTC'}</dd>
            </div>
          </dl>
        </div>

        {/* ───────────────────────────────────────────────────────────── */}
        {/* 5. ANOMALY INFORMATION                                        */}
        {/* ───────────────────────────────────────────────────────────── */}
        <div className="sensor-info-section">
          <div className="section-title">ANOMALY INFORMATION</div>
          <div className="anomaly-card">
            <div className="anomaly-col">
              <span className="anomaly-sub">ANOMALY SCORE</span>
              <span className="anomaly-score-val mono-val">
                {typeof (sensor.anomaly_score ?? sensor.anomalyScore) === 'number'
                  ? (sensor.anomaly_score ?? sensor.anomalyScore).toFixed(2)
                  : '—'}
              </span>
            </div>
            <div className="anomaly-col">
              <span className="anomaly-sub">ANOMALY STATUS</span>
              <span
                className={`anomaly-badge ${
                  (sensor.anomaly_status ?? sensor.anomalyStatus) ? 'has-anomaly' : 'no-anomaly'
                }`}
              >
                {(sensor.anomaly_status ?? sensor.anomalyStatus) || 'NOT AVAILABLE'}
              </span>
            </div>
          </div>
        </div>

        {/* ───────────────────────────────────────────────────────────── */}
        {/* 6. PHYSICAL SENSOR POSITION (REAL COORDINATES)                */}
        {/* ───────────────────────────────────────────────────────────── */}
        <div className="sensor-info-section">
          <div className="section-title">PHYSICAL SENSOR POSITION</div>
          <div className="coords-grid mono-val">
            <div className="coord-box">
              <span className="coord-axis">X</span>
              <span className="coord-val">{posX} m</span>
            </div>
            <div className="coord-box">
              <span className="coord-axis">Y</span>
              <span className="coord-val">{posY} m</span>
            </div>
            <div className="coord-box">
              <span className="coord-axis">Z</span>
              <span className="coord-val">{posZ} m</span>
            </div>
          </div>
          <span className="coord-note">
            Real physical mounting coordinates in station local coordinate space
          </span>
        </div>

        {/* ───────────────────────────────────────────────────────────── */}
        {/* 7. RECENT TELEMETRY (APACHE ECHARTS)                          */}
        {/* ───────────────────────────────────────────────────────────── */}
        <div className="sensor-info-section">
          <div className="section-title">RECENT TELEMETRY</div>
          {sensor.recentReadings && sensor.recentReadings.length > 0 ? (
            <div className="telemetry-chart-wrap">
              <div ref={chartRef} style={{ width: '100%', height: '130px' }} />
            </div>
          ) : (
            <div className="telemetry-empty-card">
              <span>NO RECENT TELEMETRY</span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};

export default SensorDetailsPanel;
