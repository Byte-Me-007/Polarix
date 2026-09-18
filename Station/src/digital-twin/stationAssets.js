/**
 * stationAssets.js — Internal infrastructure asset definitions for X-RAY and SYSTEM modes.
 *
 * Positions are RELATIVE to each zone's world position.
 * Zone world positions (center):
 *   MAIN:      [0,   7.0, 0]    sy=14  → floor at world y ≈ 0, center-relative ≈ -7
 *   ENERGY:    [0,   6.5, -30]  sy=13  → floor center-relative ≈ -6.5
 *   GENERATOR: [-30, 5.5, -30]  sy=11  → floor center-relative ≈ -5.5
 *   RESEARCH:  [38,  6.5, 0]    sy=13  → floor center-relative ≈ -6.5
 *   STORAGE:   [32,  5.5, -30]  sy=11  → floor center-relative ≈ -5.5
 *   COMMS:     [0,   5.0, -54]  sy=10  → floor center-relative ≈ -5.0
 *
 * relPos = [dx, dy, dz] where dy=0 is zone center.
 * Each asset specifies:
 *   - isPrimary: true/false for label hierarchy
 *   - labelY: height offset for floating label badge to avoid collisions
 */

export const ZONE_INTERNAL_ASSETS = {
  MAIN: [
    { id: 'HVAC-01',    type: 'HVAC',     label: 'HVAC',            relPos: [-8.5, -4.5, -4],  sensorType: 'TEMPERATURE', isPrimary: true,  labelY: 3.5 },
    { id: 'HVAC-02',    type: 'HVAC',     label: 'LIFE SUPPORT',    relPos: [ 8.5, -4.5,  5],  sensorType: 'STRAIN',      isPrimary: true,  labelY: 3.1 },
    { id: 'PANEL-01',   type: 'CONTROL',  label: 'COMMAND CONSOLE', relPos: [ 0,   -4.5,  0],  sensorType: 'STRAIN',      isPrimary: true,  labelY: 2.8 }
  ],
  ENERGY: [
    { id: 'BATT-01',   type: 'BATTERY',     label: 'BATTERY BANK',       relPos: [-7,  -3.5, -4],  sensorType: 'VOLTAGE',    isPrimary: true,  labelY: 3.7 },
    { id: 'BATT-02',   type: 'BATTERY',     label: 'BATTERY BANK B',     relPos: [-7,  -3.5,  4],  sensorType: 'VOLTAGE',    isPrimary: true,  labelY: 3.0 },
    { id: 'INV-01',    type: 'INVERTER',    label: 'MICROGRID INVERTER', relPos: [ 5.5, -4.0, -3.5],sensorType: 'POWER',    isPrimary: true,  labelY: 3.6 },
    { id: 'INV-02',    type: 'INVERTER',    label: 'SOLAR INVERTER',     relPos: [ 5.5, -4.0,  3.5],sensorType: 'IRRADIANCE',isPrimary: true,  labelY: 2.9 },
    { id: 'TRANS-01',  type: 'TRANSFORMER', label: 'HV TRANSFORMER',     relPos: [ 0,  -4.0,  0],  sensorType: 'VOLTAGE',    isPrimary: true,  labelY: 3.3 }
  ],
  GENERATOR: [
    { id: 'GEN-01',    type: 'GENERATOR', label: 'DIESEL GEN #1',    relPos: [-4.5, -3.0,  3],  sensorType: 'VIBRATION',  isPrimary: true,  labelY: 3.5 },
    { id: 'GEN-02',    type: 'GENERATOR', label: 'DIESEL GEN #2',    relPos: [ 4.5, -3.0,  3],  sensorType: 'VIBRATION',  isPrimary: true,  labelY: 3.0 },
    { id: 'FUEL-01',   type: 'FUEL_TANK', label: 'DAY TANK',         relPos: [ 0,   -2.5, -5],  sensorType: 'FLOW',       isPrimary: true,  labelY: 3.3 },
    { id: 'RAD-01',    type: 'RADIATOR',  label: 'COOLING RADIATOR', relPos: [-7.5, -3.0, -2],  sensorType: 'TEMPERATURE',isPrimary: false, labelY: 2.5 }
  ],
  RESEARCH: [
    { id: 'RES-01',    type: 'RESEARCH',  label: 'MET ARRAY',        relPos: [-4.5, -4.5, -3],  sensorType: 'HUMIDITY',   isPrimary: true,  labelY: 3.4 },
    { id: 'RES-02',    type: 'RESEARCH',  label: 'GEO STATION',      relPos: [ 4.5, -4.5,  3],  sensorType: 'MAGNETIC',   isPrimary: true,  labelY: 3.0 },
    { id: 'LAB-01',    type: 'LAB_BENCH', label: 'ATMO SAMPLER',     relPos: [ 0,   -4.5,  0],  sensorType: 'RADIATION',  isPrimary: false, labelY: 2.5 }
  ],
  STORAGE: [
    { id: 'STOR-01',   type: 'STORAGE',   label: 'FUEL RESERVE',     relPos: [-5.5, -2.5,  0],  sensorType: 'LEVEL',      isPrimary: true,  labelY: 3.5 },
    { id: 'STOR-02',   type: 'STORAGE',   label: 'WATER RESERVE',    relPos: [ 0,   -2.5, -4],  sensorType: 'LEVEL',      isPrimary: true,  labelY: 3.0 },
    { id: 'FREEZE-01', type: 'FREEZER',   label: 'CRYO FREEZER',     relPos: [ 5.5, -4.0,  3],  sensorType: 'TEMPERATURE',isPrimary: true,  labelY: 3.3 }
  ],
  COMMS: [
    { id: 'COMM-01',   type: 'COMMS',     label: 'RF SHELTER',       relPos: [-2,  -3.5, -1],   sensorType: 'SIGNAL',     isPrimary: true,  labelY: 3.3 },
    { id: 'RACK-01',   type: 'SERVER_RACK', label: 'TELEMETRY RACK', relPos: [ 2,  -3.5,  2],   sensorType: 'BANDWIDTH',  isPrimary: false, labelY: 2.6 }
  ]
};

/**
 * Resolve associated internal asset for a given sensor (e.g. ENG-MTR-002 -> DIESEL GEN #2).
 */
export const getAssociatedAssetIdForSensor = (sensor) => {
  if (!sensor) return null;
  const id = (sensor.id || '').toUpperCase();
  const name = (sensor.name || '').toUpperCase();
  const zone = (sensor.zone || '').toUpperCase();
  const type = (sensor.type || '').toUpperCase();

  // Generator zone mappings
  if (id === 'ENG-MTR-002' || name.includes('DG-2') || name.includes('GEN-2')) {
    return 'GENERATOR-GEN-02';
  }
  if (id === 'ENG-MTR-006' || name.includes('DG-1') || name.includes('GEN-1')) {
    return 'GENERATOR-GEN-01';
  }
  if (name.includes('EXHAUST') || name.includes('THERMOCOUPLE')) {
    return 'GENERATOR-GEN-01';
  }
  if (zone === 'GENERATOR' && (type === 'FLOW' || name.includes('FUEL') || name.includes('TANK'))) {
    return 'GENERATOR-FUEL-01';
  }

  // Energy zone mappings
  if (id === 'ENG-MTR-003' || name.includes('BATTERY BANK B') || name.includes('BATT B')) {
    return 'ENERGY-BATT-02';
  }
  if (name.includes('BATTERY BANK') || name.includes('BATTERY') || name.includes('BATT')) {
    return 'ENERGY-BATT-01';
  }
  if (id === 'ENG-MTR-005' || name.includes('MICROGRID') || name.includes('PHASE A')) {
    return 'ENERGY-INV-01';
  }
  if (id === 'ENG-MTR-001' || name.includes('SOLAR') || name.includes('PYRANOMETER')) {
    return 'ENERGY-INV-02';
  }
  if (name.includes('TRANSFORMER') || (type === 'VOLTAGE' && zone === 'ENERGY')) {
    return 'ENERGY-TRANS-01';
  }

  // Main zone mappings
  if (name.includes('HVAC') || (type === 'TEMPERATURE' && zone === 'MAIN')) {
    return 'MAIN-HVAC-01';
  }
  if (name.includes('LIFE SUPPORT') || name.includes('OXYGEN') || (type === 'STRAIN' && zone === 'MAIN')) {
    return 'MAIN-HVAC-02';
  }
  if (name.includes('CONSOLE') || name.includes('COMMAND')) {
    return 'MAIN-PANEL-01';
  }

  // Storage zone mappings
  if (zone === 'STORAGE' && (name.includes('FUEL') || name.includes('TANK'))) {
    return 'STORAGE-STOR-01';
  }
  if (zone === 'STORAGE' && (name.includes('WATER') || name.includes('AQUIC'))) {
    return 'STORAGE-STOR-02';
  }
  if (zone === 'STORAGE' && (name.includes('FREEZER') || name.includes('CRYO') || type === 'TEMPERATURE')) {
    return 'STORAGE-FREEZE-01';
  }

  // Comms zone mappings
  if (zone === 'COMMS' && (name.includes('RF') || name.includes('DISH') || name.includes('SIGNAL'))) {
    return 'COMMS-COMM-01';
  }
  if (zone === 'COMMS' && (name.includes('RACK') || name.includes('BANDWIDTH') || name.includes('SERVER'))) {
    return 'COMMS-RACK-01';
  }

  // Research zone mappings
  if (zone === 'RESEARCH' && (name.includes('MET') || name.includes('WIND') || type === 'HUMIDITY')) {
    return 'RESEARCH-RES-01';
  }
  if (zone === 'RESEARCH' && (name.includes('GEO') || type === 'MAGNETIC')) {
    return 'RESEARCH-RES-02';
  }
  if (zone === 'RESEARCH') {
    return 'RESEARCH-LAB-01';
  }

  return null;
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
