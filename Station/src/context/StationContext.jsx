import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { STATIONS, BASE_TELEMETRY, INITIAL_ALERTS, DEMO_SCENARIOS } from '../data/stationData';

export const DEFAULT_THRESHOLDS = {
  batteryLowPct: 45,             // % SOC critical threshold
  batteryWarnPct: 70,            // % SOC warning threshold
  fuelReserveDays: 20,           // Days: low operational threshold
  fuelReserveCriticalDays: 10,   // Days: critical reserve threshold
  generatorVibrationWarn: 3.5,   // mm/s warning threshold
  generatorVibrationCrit: 4.8,   // mm/s emergency threshold
  tempWarningC: -30.0,           // °C exterior warning threshold
  tempCriticalC: -45.0,          // °C exterior critical threshold
  sensorTimeoutSec: 180,         // Sec telemetry timeout threshold
  minBatterySocPct: 20,          // % absolute BMS safety floor
  maxBatterySocPct: 95,          // % charge absorption cutoff
  criticalLoadKw: 65.0,          // kW priority life-support load
  renewableContributionPct: 30   // % minimum renewable target mix
};

const StationContext = createContext(null);

export const StationProvider = ({ children }) => {
  const [activeStation, setActiveStation] = useState('MAITRI');
  const [activeScenario, setActiveScenario] = useState('NORMAL');
  const [alerts, setAlerts] = useState(INITIAL_ALERTS);
  const [thresholds, setThresholds] = useState(DEFAULT_THRESHOLDS);
  const [demoModeEnabled, setDemoModeEnabled] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  // Clock tick to keep timestamp fresh every 10 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      setLastUpdated(new Date());
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  const stationConfig = useMemo(() => {
    return STATIONS[activeStation] || STATIONS.MAITRI;
  }, [activeStation]);

  const telemetry = useMemo(() => {
    const base = BASE_TELEMETRY[activeStation] || BASE_TELEMETRY.MAITRI;
    const scenario = DEMO_SCENARIOS[activeScenario];

    if (!scenario || !scenario.patch || Object.keys(scenario.patch).length === 0) {
      return base;
    }

    // Merge scenario overrides cleanly over the active station's base telemetry
    return {
      ...base,
      ...scenario.patch,
      power: {
        ...base.power,
        ...(scenario.patch.power || {})
      },
      battery: {
        ...base.battery,
        ...(scenario.patch.battery || {})
      },
      fuel: {
        ...base.fuel,
        ...(scenario.patch.fuel || {})
      },
      connectivity: {
        ...base.connectivity,
        ...(scenario.patch.connectivity || scenario.patch.satellite || {})
      },
      satellite: {
        ...base.satellite,
        ...(scenario.patch.satellite || scenario.patch.connectivity || {})
      },
      environment: {
        ...base.environment,
        ...(scenario.patch.environment || scenario.patch.environmentalTelemetry || {})
      },
      environmentalTelemetry: {
        ...base.environmentalTelemetry,
        ...(scenario.patch.environmentalTelemetry || scenario.patch.environment || {})
      },
      healthCategories: scenario.patch.healthCategories || base.healthCategories,
      healthScore: scenario.patch.healthScore !== undefined ? scenario.patch.healthScore : base.healthScore,
      healthStatus: scenario.patch.healthStatus || base.healthStatus
    };
  }, [activeStation, activeScenario]);

  // Track acknowledged alert IDs across baseline and scenario alerts
  const [acknowledgedAlertIds, setAcknowledgedAlertIds] = useState(() => {
    const initial = new Set();
    INITIAL_ALERTS.forEach((a) => {
      if (a.acknowledged) initial.add(a.id);
    });
    return initial;
  });

  // Combined full alerts list (Active + Acknowledged) for active station
  const allStationAlerts = useMemo(() => {
    const scenario = DEMO_SCENARIOS[activeScenario];
    const scenarioAlerts = scenario?.addedAlerts || [];

    const mergedMap = new Map();

    alerts.forEach((a) => {
      const matches =
        a.station === activeStation ||
        a.station === 'ALL' ||
        a.station_id === activeStation ||
        a.station_id === 'ALL';
      if (matches) {
        const isAck = acknowledgedAlertIds.has(a.id) || a.acknowledged;
        mergedMap.set(a.id, {
          ...a,
          station_id: a.station_id || a.station,
          sensor_id: a.sensor_id || a.sensorId,
          acknowledged: isAck,
          status: isAck ? 'ACKNOWLEDGED' : (a.status || 'ACTIVE')
        });
      }
    });

    scenarioAlerts.forEach((a) => {
      const matches =
        a.station === activeStation ||
        a.station === 'ALL' ||
        a.station_id === activeStation ||
        a.station_id === 'ALL';
      if (matches) {
        const isAck = acknowledgedAlertIds.has(a.id) || a.acknowledged;
        mergedMap.set(a.id, {
          ...a,
          station_id: a.station_id || a.station,
          sensor_id: a.sensor_id || a.sensorId,
          acknowledged: isAck,
          status: isAck ? 'ACKNOWLEDGED' : (a.status || 'ACTIVE')
        });
      }
    });

    return Array.from(mergedMap.values());
  }, [activeStation, activeScenario, alerts, acknowledgedAlertIds]);

  // Active (unacknowledged) alerts for Dashboard and badge counts
  const activeAlerts = useMemo(() => {
    return allStationAlerts.filter((a) => !a.acknowledged);
  }, [allStationAlerts]);

  // Optional sensor-level overrides for manual test sequences (e.g. TEST 1 - TEST 6)
  const [sensorManualOverrides, setSensorManualOverrides] = useState({});

  // Dynamically derive sensor telemetry based on active station, scenario, and manual overrides
  const dynamicSensors = useMemo(() => {
    const baseSensors = stationConfig.sensors || [];
    const scenario = DEMO_SCENARIOS[activeScenario];
    const overrides = scenario?.sensorOverrides;

    return baseSensors.map((s) => {
      let updated = { ...s };

      // Apply scenario-level sensor consequences
      if (overrides) {
        if (overrides.ALL_NORMAL) {
          updated.status = 'NORMAL';
          updated.anomaly_score = 0.02;
          updated.anomalyScore = 0.02;
          updated.anomaly_status = 'NORMAL';
          updated.anomalyStatus = 'NORMAL';
          if (updated.quality === 'FAIL' || updated.quality === 'OFFLINE' || updated.quality === 'LOST') {
            updated.quality = 'GOOD';
          }
        } else if (overrides.byType && overrides.byType[s.type]) {
          const patch = overrides.byType[s.type];
          updated = { ...updated, ...patch };
          if (patch.anomaly_score !== undefined) {
            updated.anomalyScore = patch.anomaly_score;
          }
          if (patch.anomaly_status !== undefined) {
            updated.anomalyStatus = patch.anomaly_status;
          }
        } else if (overrides.byId && overrides.byId[s.id]) {
          const patch = overrides.byId[s.id];
          updated = { ...updated, ...patch };
          if (patch.anomaly_score !== undefined) {
            updated.anomalyScore = patch.anomaly_score;
          }
          if (patch.anomaly_status !== undefined) {
            updated.anomalyStatus = patch.anomaly_status;
          }
        }
      }

      // Apply manual test override (if any)
      if (sensorManualOverrides[s.id]) {
        const manual = sensorManualOverrides[s.id];
        updated = { ...updated, ...manual };
        if (manual.anomaly_score !== undefined) {
          updated.anomalyScore = manual.anomaly_score;
        }
        if (manual.anomaly_status !== undefined) {
          updated.anomalyStatus = manual.anomaly_status;
        }
      }

      // Standardize both snake_case and camelCase compatibility (Section 17)
      if (updated.anomaly_score === undefined && updated.anomalyScore !== undefined) {
        updated.anomaly_score = updated.anomalyScore;
      } else if (updated.anomalyScore === undefined && updated.anomaly_score !== undefined) {
        updated.anomalyScore = updated.anomaly_score;
      }
      if (updated.anomaly_status === undefined && updated.anomalyStatus !== undefined) {
        updated.anomaly_status = updated.anomalyStatus;
      } else if (updated.anomalyStatus === undefined && updated.anomaly_status !== undefined) {
        updated.anomalyStatus = updated.anomaly_status;
      }

      return updated;
    });
  }, [stationConfig, activeScenario, sensorManualOverrides]);

  const applyScenario = (scenarioKey) => {
    setActiveScenario(scenarioKey);
    setSensorManualOverrides({}); // Reset manual sensor overrides on scenario change
    setLastUpdated(new Date());
  };

  const updateSensor = (sensorId, patch) => {
    setSensorManualOverrides((prev) => ({
      ...prev,
      [sensorId]: { ...(prev[sensorId] || {}), ...patch }
    }));
    setLastUpdated(new Date());
  };

  const clearSensorOverrides = () => {
    setSensorManualOverrides({});
    setLastUpdated(new Date());
  };

  const acknowledgeAlert = (id) => {
    setAcknowledgedAlertIds((prev) => {
      const next = new Set(prev);
      next.add(id);
      return next;
    });

    setAlerts((prev) =>
      prev.map((a) =>
        a.id === id
          ? {
              ...a,
              acknowledged: true,
              status: 'ACKNOWLEDGED',
              acknowledgedAt: 'Just now'
            }
          : a
      )
    );
    setLastUpdated(new Date());
  };

  const handleStationChange = (newStation) => {
    if (STATIONS[newStation]) {
      setActiveStation(newStation);
      setSensorManualOverrides({}); // Cleanly reset sensor overrides across stations
      setLastUpdated(new Date());
    }
  };

  const updateThreshold = (key, val) => {
    setThresholds((prev) => ({
      ...prev,
      [key]: Number(val)
    }));
    setLastUpdated(new Date());
  };

  const updateThresholds = (newObj) => {
    setThresholds((prev) => ({
      ...prev,
      ...newObj
    }));
    setLastUpdated(new Date());
  };

  const resetThresholds = () => {
    setThresholds(DEFAULT_THRESHOLDS);
    setLastUpdated(new Date());
  };

  const resetStationState = () => {
    setActiveScenario('NORMAL');
    setSensorManualOverrides({});
    setThresholds(DEFAULT_THRESHOLDS);
    setAcknowledgedAlertIds(new Set());
    setAlerts(INITIAL_ALERTS);
    setLastUpdated(new Date());
  };

  const value = {
    activeStation,
    setActiveStation: handleStationChange,
    stationConfig,
    config: stationConfig,
    sensors: dynamicSensors,
    updateSensor,
    clearSensorOverrides,
    telemetry,
    alerts: activeAlerts, // Active unacknowledged alerts for Dashboard
    activeAlerts,
    allAlerts: allStationAlerts, // Full alerts list (Active + Acknowledged) for Alerts page
    acknowledgeAlert,
    activeScenario,
    setScenario: applyScenario,
    thresholds,
    updateThreshold,
    updateThresholds,
    resetThresholds,
    resetStationState,
    demoModeEnabled,
    setDemoModeEnabled,
    lastUpdated,
    refreshTelemetry: () => setLastUpdated(new Date())
  };

  return (
    <StationContext.Provider value={value}>
      {children}
    </StationContext.Provider>
  );
};

export const useStation = () => {
  const context = useContext(StationContext);
  if (!context) {
    throw new Error('useStation must be used within a StationProvider');
  }
  return context;
};
