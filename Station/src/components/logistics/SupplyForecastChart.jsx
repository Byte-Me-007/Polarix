import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

/**
 * SupplyForecastChart
 * ECharts 60-day forward depletion projection across key expedition stores:
 * Food, Fuel, Medical Supplies, and Critical Spares.
 * Shows critical safety threshold line and arrival horizon.
 */
export const SupplyForecastChart = ({
  nextResupplyEta = 14
}) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, null, {
        renderer: 'canvas'
      });
    }

    // Days timeline from Day 0 (Today) to Day 60
    const days = ['Day 0 (Now)', 'Day 7', 'Day 14 (ETA)', 'Day 21', 'Day 28', 'Day 35', 'Day 42', 'Day 50', 'Day 60'];

    // Depletion percentages over time
    // Food: starts 82%, depletes to 20% around day 45
    const foodCurve = [82, 74, 66, 58, 50, 42, 34, 25, 14];
    // Fuel: starts 64%, reaches critical 20% around day 18
    const fuelCurve = [64, 52, 38, 26, 15, 6, 0, 0, 0];
    // Medical Oxygen: starts 35%, dips below 20% around day 12 (Critical!)
    const medicalCurve = [35, 23, 10, 0, 0, 0, 0, 0, 0];
    // Critical Spares: starts 25%, hits 0 by day 10
    const sparesCurve = [25, 14, 0, 0, 0, 0, 0, 0, 0];

    const option = {
      backgroundColor: 'transparent',
      animationDuration: 500,
      grid: {
        top: 40,
        right: 20,
        bottom: 25,
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
              <span>${p.seriesName}: <strong>${p.value}%</strong></span>
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
        data: days,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#e5ded4' } },
        axisLabel: {
          fontFamily: 'monospace',
          fontSize: 10,
          color: '#757d85'
        }
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLine: { show: false },
        splitLine: { lineStyle: { color: '#f0ece4', type: 'dashed' } },
        axisLabel: {
          formatter: '{value}%',
          fontFamily: 'monospace',
          fontSize: 10,
          color: '#757d85'
        }
      },
      series: [
        {
          name: 'Food Rations',
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: foodCurve,
          lineStyle: { width: 2, color: '#3f6e4a' },
          itemStyle: { color: '#3f6e4a' }
        },
        {
          name: 'Polar Diesel SAB-55',
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: fuelCurve,
          lineStyle: { width: 2.5, color: '#b65a1f' },
          itemStyle: { color: '#b65a1f' }
        },
        {
          name: 'Medical Oxygen',
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: medicalCurve,
          lineStyle: { width: 2, color: '#c82a2a', type: 'dashed' },
          itemStyle: { color: '#c82a2a' }
        },
        {
          name: 'Critical Spares',
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: sparesCurve,
          lineStyle: { width: 1.5, color: '#d9821a', type: 'dotted' },
          itemStyle: { color: '#d9821a' }
        },
        // Critical Safety Buffer Reference Line (20%)
        {
          name: 'Critical Threshold (20%)',
          type: 'line',
          data: [20, 20, 20, 20, 20, 20, 20, 20, 20],
          lineStyle: { width: 1, color: '#c82a2a', type: 'dashed' },
          itemStyle: { color: '#c82a2a' },
          symbol: 'none'
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
  }, [nextResupplyEta]);

  return (
    <section className="supply-forecast-card" aria-label="Supply Consumption Forecast">
      <div className="card-header-row">
        <div>
          <h3 className="card-title">SUPPLY CONSUMPTION & DEPLETION FORECAST</h3>
          <span className="card-subtitle">
            PROJECTED 60-DAY INVENTORY TRAJECTORY & CRITICAL BUFFER CUTOFFS
          </span>
        </div>
        <div className="forecast-legend-pill">
          <span>CRITICAL CUTOFF: 20% BUFFER</span>
        </div>
      </div>

      <div ref={chartRef} className="echarts-supply-container" style={{ height: '260px', width: '100%' }} />

      <div className="forecast-footer-notes">
        <span className="forecast-note">
          ● Dotted curves indicate supplies reaching critical depletion before scheduled resupply ETA.
        </span>
      </div>
    </section>
  );
};

export default SupplyForecastChart;
