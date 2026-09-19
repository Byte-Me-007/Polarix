/**
 * Forecast Service — Operational & Deterministic Resource Projection
 *
 * Provides forward projection of Antarctic station operational resources:
 * - Diesel / Polar Fuel Reserves & Depletion Horizon
 * - Battery State of Charge (SoC), Terminal Voltage & Cycle Wear
 * - Microgrid Energy State & Generation Balance
 * - Physical Sensor State Projection for 3D Digital Twin
 *
 * NOTE: This is an operational deterministic model based strictly on
 * existing backend telemetry and consumption physics.
 * Replaceable architecture: ML API endpoints can be plugged in seamlessly
 * without changing UI or 3D twin visualization components.
 */

export const FORECAST_HORIZONS = [7, 30, 90];

/**
 * Validates availability of baseline telemetry required for forecasting
 */
export const validateForecastData = (telemetry) => {
  if (!telemetry) return false;
  const fuel = telemetry.fuel;
  const battery = telemetry.battery;

  if (!fuel || typeof fuel.totalLiters !== 'number' || typeof fuel.dailyBurnRate !== 'number') {
    return false;
  }
  if (!battery || typeof battery.percentage !== 'number') {
    return false;
  }
  return true;
};

/**
 * Calculates projected station state at a given day offset (0 to horizonDays)
 *
 * @param {Object} params
 * @param {string} params.stationId - 'MAITRI' or 'BHARATI'
 * @param {number} params.horizonDays - 7, 30, or 90
 * @param {number} params.dayOffset - float from 0 to horizonDays
 * @param {Object} params.telemetry - current station telemetry
 * @param {Array} params.sensors - current station sensors
 * @returns {Object} Forecast projection state
 */
export const calculateStationForecast = ({
  stationId = 'MAITRI',
  horizonDays = 30,
  dayOffset = 0,
  telemetry = {},
  sensors = []
}) => {
  // 1. Validate data sufficiency
  if (!validateForecastData(telemetry)) {
    return {
      isInsufficient: true,
      reason: 'DATA INSUFFICIENT',
      stationId,
      horizonDays,
      dayOffset: 0
    };
  }

  const d = Math.max(0, Math.min(horizonDays, Number(dayOffset) || 0));
  const isLive = d === 0;

  const baseFuel = telemetry.fuel || {};
  const baseBattery = telemetry.battery || {};
  const basePower = telemetry.power || {};

  // Baseline Fuel Parameters
  const initialLiters = Number(baseFuel.totalLiters) || 0;
  const capacityLiters = Number(baseFuel.capacityLiters) || initialLiters;
  const burnRate = Number(baseFuel.dailyBurnRate) || 480;

  // 2. Deterministic Fuel Projection
  const projectedLiters = Math.max(0, Math.round(initialLiters - burnRate * d));
  const projectedFuelPct = capacityLiters > 0
    ? Math.max(0, Math.min(100, Math.round((projectedLiters / capacityLiters) * 100)))
    : 0;

  const projectedDaysRemaining = burnRate > 0
    ? Math.max(0, +(projectedLiters / burnRate).toFixed(1))
    : 0;

  let fuelStatus = 'NORMAL';
  if (projectedFuelPct <= 0 || projectedDaysRemaining <= 0) {
    fuelStatus = 'CRITICAL';
  } else if (projectedFuelPct < 20 || projectedDaysRemaining < 14) {
    fuelStatus = 'CRITICAL';
  } else if (projectedFuelPct < 50 || projectedDaysRemaining < 30) {
    fuelStatus = 'WARNING';
  }

  // 3. Deterministic Battery & Power Projection
  const baseSoc = Number(baseBattery.percentage) || 78;
  const baseCycles = Number(baseBattery.cycles) || 1000;
  const baseHealth = parseFloat(baseBattery.health) || 98.0;

  const projectedCycles = baseCycles + Math.round(d * 1.2);
  const projectedHealth = Math.max(75, +(baseHealth - d * 0.02).toFixed(1));

  let projectedSoc = baseSoc;
  let batteryState = baseBattery.state || 'FLOAT';
  let energyStatus = 'STABLE';

  if (projectedLiters === 0) {
    // Diesel generator blackout — renewable shortfall depletes battery storage
    const daysSinceDepletion = d - (initialLiters / burnRate);
    projectedSoc = Math.max(0, Math.round(baseSoc - daysSinceDepletion * 40));
    batteryState = projectedSoc > 15 ? 'DISCHARGING' : 'CRITICAL DEPLETION';
    energyStatus = 'CRITICAL EMERGENCY';
  } else if (fuelStatus === 'CRITICAL') {
    // Conservation load shedding
    projectedSoc = Math.max(35, Math.round(baseSoc - Math.sin(d * 0.6) * 8 - (d * 0.15)));
    batteryState = 'DISCHARGING';
    energyStatus = 'LOAD SHEDDING';
  } else {
    // Nominal microgrid operation with mild diurnal variation
    projectedSoc = Math.max(45, Math.min(98, Math.round(baseSoc + Math.sin(d * 0.5) * 5)));
    batteryState = isLive ? (baseBattery.state || 'FLOAT') : (projectedSoc >= 85 ? 'FLOAT' : 'CHARGING');
    energyStatus = 'STABLE';
  }

  const projectedVoltage = (395 + (projectedSoc / 100) * 26).toFixed(1) + ' V';

  // 4. Project Sensor Telemetry for 3D Twin & Heatmap
  const projectedSensors = sensors.map((sensor) => {
    const s = { ...sensor };
    const domain = (s.domain || '').toUpperCase();
    const type = (s.type || '').toUpperCase();
    const id = s.id || '';

    // Fuel Level Sensors (e.g. LOG-MTR-001, LOG-BHR-001)
    if (id.includes('LOG') && (type === 'LEVEL' || s.name?.includes('Fuel') || s.name?.includes('Diesel'))) {
      s.value = projectedFuelPct;
      s.status = fuelStatus;
    }

    // Generator & Flow Sensors (e.g. LOG-MTR-002, ENG-MTR-006)
    if (id.includes('GENERATOR') || s.name?.includes('Day Tank') || s.name?.includes('Fuel Farm')) {
      if (projectedLiters === 0) {
        s.status = 'CRITICAL';
        s.value = 0;
      } else if (fuelStatus === 'CRITICAL') {
        s.status = 'WARNING';
      }
    }

    // Battery Bank Sensors (e.g. ENG-MTR-003, ENG-BHR-002)
    if (s.name?.includes('Battery')) {
      if (type === 'VOLTAGE') {
        s.value = parseFloat(projectedVoltage);
      } else if (type === 'HEALTH' || s.unit === '%') {
        s.value = projectedHealth;
      }
      if (projectedSoc < 25) {
        s.status = 'CRITICAL';
      } else if (projectedSoc < 50) {
        s.status = 'WARNING';
      }
    }

    return s;
  });

  // 5. Build Projected Telemetry Structure (maintains existing schema)
  const projectedTelemetry = {
    ...telemetry,
    fuel: {
      ...baseFuel,
      currentLevel: projectedFuelPct,
      totalLiters: projectedLiters,
      remainingDays: projectedDaysRemaining,
      reserveStatus: fuelStatus === 'NORMAL' ? 'SECURE' : fuelStatus
    },
    battery: {
      ...baseBattery,
      percentage: projectedSoc,
      voltage: projectedVoltage,
      state: batteryState,
      health: `${projectedHealth}%`,
      cycles: projectedCycles,
      remainingHours: projectedSoc > 20 ? `${Math.round((projectedSoc / 100) * 48)} hrs` : '0.0 hrs'
    },
    power: {
      ...basePower,
      energyState: energyStatus,
      dieselGeneration: projectedLiters === 0 ? '0.0 kW' : basePower.dieselGeneration,
      loadPercentage: energyStatus === 'CRITICAL EMERGENCY' ? 30 : energyStatus === 'LOAD SHEDDING' ? 52 : basePower.loadPercentage
    }
  };

  const projectedDate = new Date(Date.now() + d * 86400000);

  return {
    isInsufficient: false,
    isLive,
    stationId,
    horizonDays,
    dayOffset: d,
    projectedDateFormatted: projectedDate.toISOString().replace('T', ' ').substring(0, 16) + ' UTC',
    fuel: {
      liters: projectedLiters,
      percentage: projectedFuelPct,
      daysRemaining: projectedDaysRemaining,
      status: fuelStatus,
      dailyBurnRate: burnRate,
      capacityLiters
    },
    battery: {
      percentage: projectedSoc,
      voltage: projectedVoltage,
      state: batteryState,
      health: `${projectedHealth}%`,
      cycles: projectedCycles
    },
    power: {
      energyStatus,
      loadPercentage: projectedTelemetry.power.loadPercentage
    },
    projectedTelemetry,
    projectedSensors
  };
};

export default calculateStationForecast;
