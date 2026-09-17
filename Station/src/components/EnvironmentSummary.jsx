import React, { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';
import { useStationTelemetry } from '../hooks/useStationTelemetry';
import { generate24HourTelemetry } from '../data/stationData';

export const EnvironmentSummary = () => {
  const { telemetry, activeStation } = useStationTelemetry();
  const env = telemetry.environmentalTelemetry || telemetry.environment || {};
  const chartRef = useRef(null);
  const chartInstance = useRef(null);
  const [activeMetricFocus, setActiveMetricFocus] = useState('ALL');

  useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, null, {
        renderer: 'canvas'
      });
    }

    const baseTemp = env.temperature !== undefined ? env.temperature : -18.4;
    const baseWind = env.windSpeed !== undefined ? env.windSpeed : 42.5;

    const { hours, temps, winds, pressures, humidities } = generate24HourTelemetry(
      baseTemp,
      baseWind
    );

    // Build series based on focus selection (NO BLUE!)
    const allSeries = [
      {
        name: 'Temperature (°C)',
        id: 'temp',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: temps,
        lineStyle: { width: 2.2, color: '#b65a1f' }, // Polaris Copper
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(182, 90, 31, 0.14)' },
            { offset: 1, color: 'rgba(182, 90, 31, 0.00)' }
          ])
        }
      },
      {
        name: 'Wind Speed (km/h)',
        id: 'wind',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        showSymbol: false,
        data: winds,
        lineStyle: { width: 1.8, color: '#4f6f52' }, // Polaris Sage
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(79, 111, 82, 0.10)' },
            { offset: 1, color: 'rgba(79, 111, 82, 0.00)' }
          ])
        }
      },
      {
        name: 'Barometric Pressure (hPa)',
        id: 'pressure',
        type: 'line',
        yAxisIndex: 0,
        smooth: true,
        showSymbol: false,
        data: pressures.map(p => Number((p - 1000).toFixed(1))), // Delta display
        lineStyle: { width: 1.2, color: '#727b87', type: 'dashed' }
      }
    ];

    const filteredSeries = activeMetricFocus === 'ALL'
      ? allSeries
      : allSeries.filter(s => {
          if (activeMetricFocus === 'TEMP') return s.id === 'temp';
          if (activeMetricFocus === 'WIND') return s.id === 'wind';
          if (activeMetricFocus === 'PRESSURE') return s.id === 'pressure';
          return true;
        });

    const option = {
      backgroundColor: 'transparent',
      animationDuration: 400,
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#ffffff',
        borderColor: '#e2ddd4',
        borderWidth: 1,
        padding: [10, 14],
        textStyle: { 
          color: '#191c20', 
          fontFamily: 'JetBrains Mono', 
          fontSize: 12 
        },
        axisPointer: {
          lineStyle: { color: '#b65a1f', width: 1, type: 'dashed' }
        },
        extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.06); border-radius: 4px;'
      },
      legend: {
        show: true,
        top: 0,
        right: 12,
        icon: 'rect',
        itemWidth: 12,
        itemHeight: 3,
        textStyle: { color: '#4b525d', fontSize: 11, fontFamily: 'Inter' }
      },
      grid: {
        top: 36,
        left: '2%',
        right: '2%',
        bottom: '2%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: hours,
        axisLine: { lineStyle: { color: '#e2ddd4' } },
        axisTick: { lineStyle: { color: '#e2ddd4' } },
        axisLabel: { color: '#727b87', fontSize: 10, fontFamily: 'JetBrains Mono' }
      },
      yAxis: [
        {
          type: 'value',
          name: 'Temp (°C) / Pres. Δ',
          nameTextStyle: { color: '#727b87', fontSize: 10, align: 'left' },
          position: 'left',
          splitLine: { lineStyle: { color: '#f2efe7', type: 'solid' } },
          axisLine: { show: false },
          axisLabel: {
            color: '#727b87',
            fontSize: 10,
            fontFamily: 'JetBrains Mono',
            formatter: '{value}°C'
          }
        },
        {
          type: 'value',
          name: 'Wind (km/h)',
          nameTextStyle: { color: '#727b87', fontSize: 10, align: 'right' },
          position: 'right',
          splitLine: { show: false },
          axisLine: { show: false },
          axisLabel: {
            color: '#727b87',
            fontSize: 10,
            fontFamily: 'JetBrains Mono',
            formatter: '{value}'
          }
        }
      ],
      series: filteredSeries
    };

    chartInstance.current.setOption(option, true);

    const handleResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [env.temperature, env.windSpeed, activeMetricFocus, activeStation]);

  return (
    <section className="analytical-section" id="environmental-telemetry-section">
      {/* Header with Title & Metric Focus Tabs */}
      <div className="analytical-header-bar">
        <div className="analytical-title-group">
          <h2>ENVIRONMENTAL TELEMETRY</h2>
          <div className="analytical-subtitle">24 HOUR OBSERVATION WINDOW</div>
        </div>

        {/* Metric Focus Selector */}
        <div className="metric-selector-tabs" role="tablist">
          {[
            { id: 'ALL', label: 'ALL SENSORS' },
            { id: 'TEMP', label: 'TEMPERATURE' },
            { id: 'WIND', label: 'WIND SPEED' },
            { id: 'PRESSURE', label: 'BAROMETRIC' }
          ].map(tab => (
            <button
              key={tab.id}
              type="button"
              className={`metric-tab-pill ${activeMetricFocus === tab.id ? 'active' : ''}`}
              onClick={() => setActiveMetricFocus(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Observation Quadrants Readout Strip */}
      <div className="quadrant-readout-strip">
        {/* 1. Temperature */}
        <div className="quadrant-cell">
          <div className="quadrant-label">
            <span>TEMPERATURE</span>
            <span style={{ color: 'var(--polaris-copper)' }}>●</span>
          </div>
          <div className="quadrant-value">
            {env.temperature ?? -18.4}
            <span className="unit">{env.temperatureUnit || '°C'}</span>
          </div>
          <div className="quadrant-sub">
            FEELS LIKE: {env.feelsLike || '-28.1°C'}
          </div>
        </div>

        {/* 2. Wind Speed */}
        <div className="quadrant-cell">
          <div className="quadrant-label">
            <span>WIND SPEED</span>
            <span style={{ color: 'var(--polaris-sage)' }}>●</span>
          </div>
          <div className="quadrant-value">
            {env.windSpeed ?? 42.5}
            <span className="unit">{env.windSpeedUnit || 'km/h'}</span>
          </div>
          <div className="quadrant-sub">
            VECTOR: {env.windDirection || 'SSE (158°)'}
          </div>
        </div>

        {/* 3. Barometric Pressure */}
        <div className="quadrant-cell">
          <div className="quadrant-label">
            <span>BAROMETRIC PRESSURE</span>
            <span style={{ color: 'var(--polaris-text-muted)' }}>●</span>
          </div>
          <div className="quadrant-value">
            {env.pressure ?? 986.2}
            <span className="unit">{env.pressureUnit || 'hPa'}</span>
          </div>
          <div className="quadrant-sub">
            SOLAR IRRADIANCE: {env.solarRadiation || 420} W/m²
          </div>
        </div>

        {/* 4. Relative Humidity */}
        <div className="quadrant-cell">
          <div className="quadrant-label">
            <span>RELATIVE HUMIDITY</span>
            <span style={{ color: 'var(--polaris-text-muted)' }}>●</span>
          </div>
          <div className="quadrant-value">
            {env.humidity ?? 58}
            <span className="unit">{env.humidityUnit || '%'}</span>
          </div>
          <div className="quadrant-sub">
            VISIBILITY: {env.visibility || '24 km'}
          </div>
        </div>
      </div>

      {/* Single Cohesive Analytical ECharts Visualization */}
      <div ref={chartRef} className="echarts-scientific-container" />
    </section>
  );
};

export default EnvironmentSummary;
