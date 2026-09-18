import React from 'react';
import { useStation } from '../context/StationContext';

/**
 * AssetInspectPanel — compact infrastructure asset inspection overlay.
 *
 * Appears when an internal asset marker is clicked in X-RAY or SYSTEM mode.
 * Pulls real telemetry from StationContext. Never invents values.
 *
 * Props:
 *   asset       — { id, type, label, zone, status }
 *   onClose     — callback
 */

const ASSET_SENSOR_MAP = {
  // Maps asset type to sensor id prefix or domain for telemetry lookup
  GENERATOR:  { domain: 'ENERGY',       zone: 'GENERATOR',  sensorTypes: ['VIBRATION', 'PRESSURE', 'TEMPERATURE'] },
  BATTERY:    { domain: 'ENERGY',       zone: 'ENERGY',     sensorTypes: ['VOLTAGE', 'HEALTH'] },
  INVERTER:   { domain: 'ENERGY',       zone: 'ENERGY',     sensorTypes: ['VOLTAGE', 'POWER'] },
  HVAC:       { domain: 'STRUCTURE',    zone: 'MAIN',       sensorTypes: ['TEMPERATURE', 'STRAIN'] },
  RESEARCH:   { domain: 'ENVIRONMENT',  zone: 'RESEARCH',   sensorTypes: ['HUMIDITY', 'RADIATION', 'MAGNETIC'] },
  COMMS:      { domain: 'CONNECTIVITY', zone: 'COMMS',      sensorTypes: ['SIGNAL', 'ANGLE', 'BANDWIDTH'] },
  STORAGE:    { domain: 'LOGISTICS',    zone: 'STORAGE',    sensorTypes: ['LEVEL', 'TEMPERATURE'] },
  FUEL_TANK:  { domain: 'LOGISTICS',    zone: 'STORAGE',    sensorTypes: ['LEVEL', 'FLOW'] }
};

const STATUS_META = {
  RUNNING:  { label: 'RUNNING',   color: '#4f6f52', bg: 'rgba(79,111,82,0.08)',   border: 'rgba(79,111,82,0.25)'   },
  NORMAL:   { label: 'NOMINAL',   color: '#4f6f52', bg: 'rgba(79,111,82,0.08)',   border: 'rgba(79,111,82,0.25)'   },
  CHARGING: { label: 'CHARGING',  color: '#4f6f52', bg: 'rgba(79,111,82,0.08)',   border: 'rgba(79,111,82,0.25)'   },
  WARNING:  { label: 'WARNING',   color: '#b26814', bg: 'rgba(178,104,20,0.08)',  border: 'rgba(178,104,20,0.25)'  },
  CRITICAL: { label: 'CRITICAL',  color: '#b5382b', bg: 'rgba(181,56,43,0.08)',   border: 'rgba(181,56,43,0.25)'   },
  OFFLINE:  { label: 'OFFLINE',   color: '#5d6672', bg: 'rgba(93,102,114,0.08)', border: 'rgba(93,102,114,0.25)'  }
};

// Derive key telemetry lines from sensors matching this asset's zone+domain
const getAssetTelemetry = (assetType, sensors, telemetry) => {
  const map = ASSET_SENSOR_MAP[assetType];
  if (!map) return [];

  const lines = [];

  if (assetType === 'GENERATOR') {
    const vib = sensors.find(s => s.zone === 'GENERATOR' && s.type === 'VIBRATION');
    const fuel = sensors.find(s => s.zone === 'GENERATOR' && s.type === 'PRESSURE');
    const exhaust = sensors.find(s => s.zone === 'GENERATOR' && s.type === 'TEMPERATURE');
    if (vib) lines.push({ label: 'VIBRATION', value: `${vib.value} ${vib.unit}`, status: vib.status });
    if (fuel) lines.push({ label: 'FUEL PRESS', value: `${fuel.value} ${fuel.unit}`, status: fuel.status });
    if (exhaust) lines.push({ label: 'EXHAUST TEMP', value: `${exhaust.value} ${exhaust.unit}`, status: exhaust.status });
    const power = telemetry?.power;
    if (power?.dieselGeneration) lines.push({ label: 'OUTPUT', value: power.dieselGeneration, status: 'NORMAL' });
  } else if (assetType === 'BATTERY') {
    const batt = telemetry?.battery || {};
    if (batt.percentage != null) lines.push({ label: 'STATE OF CHARGE', value: `${batt.percentage}%`, status: batt.percentage < 30 ? 'CRITICAL' : batt.percentage < 55 ? 'WARNING' : 'NORMAL' });
    if (batt.voltage) lines.push({ label: 'VOLTAGE', value: batt.voltage, status: 'NORMAL' });
    if (batt.current) lines.push({ label: 'CURRENT', value: batt.current, status: 'NORMAL' });
    if (batt.state) lines.push({ label: 'BATTERY STATE', value: batt.state, status: 'NORMAL' });
    if (batt.remainingHours) lines.push({ label: 'REMAINING', value: batt.remainingHours, status: 'NORMAL' });
  } else if (assetType === 'INVERTER') {
    const inv = sensors.find(s => s.zone === 'ENERGY' && s.type === 'VOLTAGE');
    if (inv) lines.push({ label: 'BUS VOLTAGE', value: `${inv.value} ${inv.unit}`, status: inv.status });
    const pw = sensors.find(s => s.zone === 'ENERGY' && s.type === 'POWER');
    if (pw) lines.push({ label: 'POWER FACTOR', value: `${pw.value} ${pw.unit}`, status: pw.status });
    const solar = sensors.find(s => s.type === 'IRRADIANCE');
    if (solar) lines.push({ label: 'IRRADIANCE', value: `${solar.value} ${solar.unit}`, status: solar.status });
  } else if (assetType === 'HVAC') {
    const temp = sensors.find(s => s.zone === 'MAIN' && s.type === 'TEMPERATURE');
    if (temp) lines.push({ label: 'HABITAT TEMP', value: `${temp.value} ${temp.unit}`, status: temp.status });
    const strain = sensors.find(s => s.zone === 'MAIN' && s.type === 'STRAIN');
    if (strain) lines.push({ label: 'STRUCT STRAIN', value: `${strain.value} ${strain.unit}`, status: strain.status });
  } else if (assetType === 'RESEARCH') {
    const hum = sensors.find(s => s.zone === 'RESEARCH' && s.type === 'HUMIDITY');
    if (hum) lines.push({ label: 'HUMIDITY', value: `${hum.value} ${hum.unit}`, status: hum.status });
    const rad = sensors.find(s => s.type === 'RADIATION');
    if (rad) lines.push({ label: 'OZONE', value: `${rad.value} ${rad.unit}`, status: rad.status });
    const mag = sensors.find(s => s.type === 'MAGNETIC');
    if (mag) lines.push({ label: 'GEOMAGNETIC', value: `${mag.value} ${mag.unit}`, status: mag.status });
  } else if (assetType === 'COMMS') {
    const sig = sensors.find(s => s.zone === 'COMMS' && s.type === 'SIGNAL');
    if (sig) lines.push({ label: 'SIGNAL SNR', value: `${sig.value} ${sig.unit}`, status: sig.status });
    const ang = sensors.find(s => s.zone === 'COMMS' && s.type === 'ANGLE');
    if (ang) lines.push({ label: 'DISH ELEV', value: `${ang.value} ${ang.unit}`, status: ang.status });
    const bw = sensors.find(s => s.type === 'BANDWIDTH');
    if (bw) lines.push({ label: 'DOWNLINK', value: `${bw.value} ${bw.unit}`, status: bw.status });
    const sat = telemetry?.satellite;
    if (sat?.latency) lines.push({ label: 'LATENCY', value: sat.latency, status: sat.status === 'OFFLINE' ? 'OFFLINE' : 'NORMAL' });
  } else if (assetType === 'STORAGE' || assetType === 'FUEL_TANK') {
    const fuel = sensors.find(s => s.zone === 'STORAGE' && s.type === 'LEVEL');
    if (fuel) lines.push({ label: 'FUEL RESERVE', value: `${fuel.value} ${fuel.unit}`, status: fuel.status });
    const water = sensors.find(s => s.zone === 'STORAGE' && s.type === 'LEVEL' && s.id !== (fuel?.id));
    if (water) lines.push({ label: 'WATER RESERVE', value: `${water.value} ${water.unit}`, status: water.status });
    const temp = sensors.find(s => s.zone === 'STORAGE' && s.type === 'TEMPERATURE');
    if (temp) lines.push({ label: 'FREEZER TEMP', value: `${temp.value} ${temp.unit}`, status: temp.status });
    const fuelTelemetry = telemetry?.fuel;
    if (fuelTelemetry?.remainingDays != null) lines.push({ label: 'FUEL DAYS', value: `${fuelTelemetry.remainingDays} days`, status: fuelTelemetry.remainingDays < 10 ? 'CRITICAL' : fuelTelemetry.remainingDays < 20 ? 'WARNING' : 'NORMAL' });
  }

  return lines;
};

const DataRow = ({ label, value, status }) => {
  const col = STATUS_META[status?.toUpperCase()]?.color || '#4b525d';
  return (
    <div className="asset-panel-data-row">
      <span className="asset-panel-data-label">{label}</span>
      <span className="asset-panel-data-value" style={{ color: status && status !== 'NORMAL' ? col : '#191c20' }}>
        {value}
      </span>
    </div>
  );
};

export const AssetInspectPanel = ({ asset, onClose }) => {
  const { sensors, telemetry } = useStation();
  if (!asset) return null;

  const statusKey = (asset.status || 'RUNNING').toUpperCase();
  const sm = STATUS_META[statusKey] || STATUS_META.RUNNING;

  const telemetryLines = getAssetTelemetry(asset.type, sensors, telemetry);

  return (
    <div className="asset-inspect-panel">
      {/* Header */}
      <div className="asset-panel-header">
        <div className="asset-panel-title-row">
          <div className="asset-panel-icon-wrap" style={{ background: sm.bg, borderColor: sm.border }}>
            <span style={{ color: sm.color, fontSize: '12px' }}>
              {asset.type === 'GENERATOR' ? '⚙' :
               asset.type === 'BATTERY'   ? '⬡' :
               asset.type === 'HVAC'      ? '◈' :
               asset.type === 'RESEARCH'  ? '◉' :
               asset.type === 'COMMS'     ? '◎' :
               asset.type === 'INVERTER'  ? '⊞' :
               '▪'}
            </span>
          </div>
          <div>
            <div className="asset-panel-label">{asset.label}</div>
            <div className="asset-panel-zone">{asset.zone} ZONE — {asset.id}</div>
          </div>
        </div>
        <button className="asset-panel-close" onClick={onClose} title="Close inspection panel">×</button>
      </div>

      {/* Status badge */}
      <div className="asset-panel-status-row">
        <span
          className="asset-panel-status-badge"
          style={{ color: sm.color, background: sm.bg, borderColor: sm.border }}
        >
          {sm.label}
        </span>
        <span className="asset-panel-type-tag">{asset.type.replace('_', ' ')}</span>
      </div>

      {/* Telemetry lines */}
      <div className="asset-panel-telemetry">
        {telemetryLines.length > 0 ? (
          telemetryLines.map((row, i) => (
            <DataRow key={i} label={row.label} value={row.value} status={row.status} />
          ))
        ) : (
          <div className="asset-panel-unavailable">DATA UNAVAILABLE</div>
        )}
      </div>

      <div className="asset-panel-footer">
        Live telemetry • No fabricated values
      </div>
    </div>
  );
};

export default AssetInspectPanel;
