/**
 * stationAssets.js — Internal infrastructure asset definitions for X-RAY and SYSTEM modes.
 *
 * Positions are RELATIVE to each zone's world position.
 * Buildings are now taller (14-11 units height), so assets sit at floor level
 * which is approximately py - (sy/2) relative to zone center, i.e. around -5 to -4 below center.
 *
 * Zone world positions (center):
 *   MAIN:      [0,   7.0, 0]    sy=14  → floor at world y ≈ 0, center-relative ≈ -7
 *   ENERGY:    [0,   6.5, -30]  sy=13  → floor center-relative ≈ -6.5
 *   GENERATOR: [-30, 5.5, -30]  sy=11  → floor center-relative ≈ -5.5
 *   RESEARCH:  [38,  6.5, 0]    sy=13  → floor center-relative ≈ -6.5
 *   STORAGE:   [32,  5.5, -30]  sy=11  → floor center-relative ≈ -5.5
 *   COMMS:     [0,   5.0, -54]  sy=10  → floor center-relative ≈ -5.0
 *
 * relPos = [dx, dy, dz] where dy=0 is zone center → assets at dy = -floor_offset + asset_height/2
 */
export const ZONE_INTERNAL_ASSETS = {
  MAIN: [
    { id: 'HVAC-01',    type: 'HVAC',     label: 'HVAC UNIT A',     relPos: [-8,  -4.5, -4],  sensorType: 'TEMPERATURE' },
    { id: 'HVAC-02',    type: 'HVAC',     label: 'LIFE SUPPORT SYS', relPos: [ 8,  -4.5,  5],  sensorType: 'STRAIN' },
    { id: 'PANEL-01',   type: 'CONTROL',  label: 'COMMAND CONSOLE',  relPos: [ 0,  -4.5,  0],  sensorType: 'STRAIN' }
  ],
  ENERGY: [
    { id: 'BATT-01',   type: 'BATTERY',  label: 'BATTERY BANK A',   relPos: [-7,  -3.5, -4],  sensorType: 'VOLTAGE' },
    { id: 'BATT-02',   type: 'BATTERY',  label: 'BATTERY BANK B',   relPos: [-7,  -3.5,  4],  sensorType: 'VOLTAGE' },
    { id: 'INV-01',    type: 'INVERTER', label: 'MICROGRID INV.',    relPos: [ 5,  -4.0, -3],  sensorType: 'POWER' },
    { id: 'INV-02',    type: 'INVERTER', label: 'SOLAR INVERTER',    relPos: [ 5,  -4.0,  3],  sensorType: 'IRRADIANCE' },
    { id: 'TRANS-01',  type: 'TRANSFORMER', label: 'HV TRANSFORMER', relPos: [ 0,  -4.0,  0],  sensorType: 'VOLTAGE' }
  ],
  GENERATOR: [
    { id: 'GEN-01',    type: 'GENERATOR', label: 'DIESEL GEN #1',    relPos: [-4,  -3.0,  3],  sensorType: 'VIBRATION' },
    { id: 'GEN-02',    type: 'GENERATOR', label: 'DIESEL GEN #2',    relPos: [ 4,  -3.0,  3],  sensorType: 'VIBRATION' },
    { id: 'FUEL-01',   type: 'FUEL_TANK', label: 'DAY TANK',         relPos: [ 0,  -2.5, -5],  sensorType: 'FLOW' },
    { id: 'RAD-01',    type: 'RADIATOR',  label: 'COOLING RADIATOR', relPos: [-7.5, -3.0, 0],  sensorType: 'TEMPERATURE' }
  ],
  RESEARCH: [
    { id: 'RES-01',    type: 'RESEARCH',  label: 'MET ARRAY',        relPos: [-4,  -4.5, -3],  sensorType: 'HUMIDITY' },
    { id: 'RES-02',    type: 'RESEARCH',  label: 'GEO STATION',      relPos: [ 4,  -4.5,  3],  sensorType: 'MAGNETIC' },
    { id: 'LAB-01',    type: 'LAB_BENCH', label: 'ATMO SAMPLER',     relPos: [ 0,  -4.5,  0],  sensorType: 'RADIATION' }
  ],
  STORAGE: [
    { id: 'STOR-01',   type: 'STORAGE',   label: 'FUEL RESERVE',     relPos: [-5,  -2.5,  0],  sensorType: 'LEVEL' },
    { id: 'STOR-02',   type: 'STORAGE',   label: 'WATER RESERVE',    relPos: [ 0,  -2.5, -4],  sensorType: 'LEVEL' },
    { id: 'FREEZE-01', type: 'FREEZER',   label: 'CRYO FREEZER',     relPos: [ 5,  -4.0,  3],  sensorType: 'TEMPERATURE' }
  ],
  COMMS: [
    { id: 'COMM-01',   type: 'COMMS',     label: 'RF SHELTER',       relPos: [-2,  -3.5, -2],  sensorType: 'SIGNAL' },
    { id: 'RACK-01',   type: 'SERVER_RACK', label: 'TELEMETRY RACK', relPos: [ 2,  -3.5,  2],  sensorType: 'BANDWIDTH' }
  ]
};

/**
 * Resolve asset status from live sensors list.
 */
export const resolveAssetStatus = (asset, zoneCode, sensors, telemetry) => {
  if (!sensors || sensors.length === 0) return 'RUNNING';

  if (asset.type === 'BATTERY') {
    const batt = telemetry?.battery;
    if (!batt) return 'RUNNING';
    if (batt.percentage < 30) return 'CRITICAL';
    if (batt.percentage < 55) return 'WARNING';
    return 'RUNNING';
  }
  if (asset.type === 'GENERATOR') {
    const power = telemetry?.power;
    const dieselKW = parseFloat((power?.dieselGeneration || '0').toString().replace(/[^0-9.]/g, '')) || 0;
    if (dieselKW < 0.5) return 'OFFLINE';
  }
  if (asset.type === 'COMMS' || asset.type === 'SERVER_RACK') {
    const sat = telemetry?.satellite || telemetry?.connectivity;
    if (sat?.status === 'OFFLINE') return 'OFFLINE';
  }

  const matchingSensor = sensors.find(
    s => s.zone === zoneCode && s.type === asset.sensorType
  );
  if (!matchingSensor) return 'RUNNING';

  const st = matchingSensor.status?.toUpperCase();
  if (st === 'CRITICAL') return 'CRITICAL';
  if (st === 'WARNING')  return 'WARNING';
  if (st === 'OFFLINE')  return 'OFFLINE';
  return 'RUNNING';
};
