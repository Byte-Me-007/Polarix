import React, { useEffect, useRef, useMemo } from 'react';
import * as echarts from 'echarts';

/**
 * EnergyLoadProfileChart
 * High-precision 24-hour load and generation trend line chart utilizing ECharts.
 * Shows Current, Average, and Peak demand callouts.
 */
export const EnergyLoadProfileChart = ({
  loadKw = 84.3,
  totalGenKw = 84.3,
  solarKw = 42.8,
  windKw = 18.4,
  peakLoad = 89.2
}) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  // Generate 24-hour deterministic timeline around current telemetry
  const { hours, loadSeries, genSeries, avgLoad } = useMemo(() => {
    const hrs = [
      '00:00', '02:00', '04:00', '06:00', '08:00', '10:00',
      '12:00', '14:00', '16:00', '18:00', '20:00', '22:00', 'NOW'
    ];

    // Curve simulating diurnal solar and station activity
    const lSeries = [
      68.2, 65.4, 64.0, 71.2, 78.5, 82.0,
      86.4, 85.0, 81.2, 79.5, 82.4, 76.0, loadKw
    ];

    const gSeries = [
      48.0, 46.5, 45.0, 58.0, 74.5, 86.0,
      92.0, 90.5, 84.0, 78.0, 72.5, 68.0, totalGenKw
    ];

    const sum = lSeries.reduce((a, b) => a + b, 0);
    const avg = Number((sum / lSeries.length).toFixed(1));

    return {
      hours: hrs,
      loadSeries: lSeries,
      genSeries: gSeries,
      avgLoad: avg
    };
  }, [loadKw, totalGenKw]);

  useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, null, {
        renderer: 'canvas'
      });
    }

    const option = {
      backgroundColor: 'transparent',
      animationDuration: 500,
      grid: {
        top: 36,
        right: 20,
        bottom: 24,
        left: 45,
        containLabel: false
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#ffffff',
        borderColor: '#e5ded4',
        borderWidth: 1,
        padding: [6, 10],
        textStyle: {
          fontFamily: 'monospace',
          fontSize: 12,
          color: '#191c20'
        },
        formatter: (params) => {
          let html = `<div style="font-weight:700;margin-bottom:4px">${params[0].name}</div>`;
          params.forEach((p) => {
            html += `<div style="display:flex;align-items:center;gap:6px;font-size:11px">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color}"></span>
              <span>${p.seriesName}: <strong>${p.value} kW</strong></span>
            </div>`;
          });
          return html;
        }
      },
      legend: {
        top: 0,
        right: 10,
        icon: 'rect',
        itemWidth: 12,
        itemHeight: 4,
        textStyle: {
          fontFamily: 'monospace',
          fontSize: 11,
          color: '#5d6672'
        }
      },
      xAxis: {
        type: 'category',
        data: hours,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#e5ded4' } },
        axisLabel: {
          color: '#8a929e',
          fontFamily: 'monospace',
          fontSize: 10
        }
      },
      yAxis: {
        type: 'value',
        name: 'POWER (kW)',
        nameTextStyle: {
          color: '#8a929e',
          fontFamily: 'monospace',
          fontSize: 9,
          padding: [0, 0, 4, 0]
        },
        splitLine: { lineStyle: { color: '#f0ece3', type: 'dashed' } },
        axisLabel: {
          color: '#8a929e',
          fontFamily: 'monospace',
          fontSize: 10
        }
      },
      series: [
        {
          name: 'Station Load',
          type: 'line',
          smooth: 0.25,
          data: loadSeries,
          symbol: 'circle',
          symbolSize: 4,
          itemStyle: { color: '#191c20' },
          lineStyle: { width: 2, color: '#191c20' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(25, 28, 32, 0.08)' },
              { offset: 1, color: 'rgba(25, 28, 32, 0.00)' }
            ])
          }
        },
        {
          name: 'Total Generation',
          type: 'line',
          smooth: 0.25,
          data: genSeries,
          symbol: 'circle',
          symbolSize: 4,
          itemStyle: { color: '#3f6e4a' },
          lineStyle: { width: 2, color: '#3f6e4a' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(63, 110, 74, 0.12)' },
              { offset: 1, color: 'rgba(63, 110, 74, 0.00)' }
            ])
          }
        }
      ]
    };

    chartInstance.current.setOption(option);

    const handleResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
    };
  }, [hours, loadSeries, genSeries]);

  return (
    <section className="energy-chart-card" aria-label="24-Hour Load Profile Chart">
      <div className="card-header-row">
        <div className="chart-title-wrap">
          <h3 className="card-title">24-HOUR LOAD & GENERATION PROFILE</h3>
          <span className="card-subtitle">
            DIURNAL MICROGRID DEMAND TRACKING (UTC)
          </span>
        </div>

        <div className="chart-callouts">
          <div className="callout-pill">
            <span className="callout-label">CURRENT</span>
            <span className="callout-val">{loadKw.toFixed(1)} kW</span>
          </div>
          <div className="callout-pill">
            <span className="callout-label">AVERAGE</span>
            <span className="callout-val">{avgLoad.toFixed(1)} kW</span>
          </div>
          <div className="callout-pill peak">
            <span className="callout-label">PEAK</span>
            <span className="callout-val">{typeof peakLoad === 'number' ? `${peakLoad} kW` : peakLoad}</span>
          </div>
        </div>
      </div>

      <div ref={chartRef} className="echarts-energy-container" style={{ height: '260px', width: '100%' }} />
    </section>
  );
};

export default EnergyLoadProfileChart;
