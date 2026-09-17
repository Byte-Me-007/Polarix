import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { STATIONS, BASE_TELEMETRY, INITIAL_ALERTS, DEMO_SCENARIOS } from '../data/stationData';

const StationContext = createContext(null);

export const StationProvider = ({ children }) => {
  const [activeStation, setActiveStation] = useState('MAITRI');
  const [activeScenario, setActiveScenario] = useState('NORMAL');
  const [alerts, setAlerts] = useState(INITIAL_ALERTS);
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

  // Combined alerts: station-specific alerts + scenario additions
  const activeAlertsList = useMemo(() => {
    const scenario = DEMO_SCENARIOS[activeScenario];
    const scenarioAlerts = scenario?.addedAlerts || [];
    return [...scenarioAlerts, ...alerts].filter(
      (a) => a.station === activeStation || a.station === 'ALL'
    );
  }, [activeStation, activeScenario, alerts]);

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
    setAlerts((prev) =>
      prev.map((a) => (a.id === id ? { ...a, acknowledged: true } : a))
    );
  };

  const handleStationChange = (newStation) => {
    if (STATIONS[newStation]) {
      setActiveStation(newStation);
      setSensorManualOverrides({}); // Cleanly reset sensor overrides across stations
      setLastUpdated(new Date());
    }
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
    alerts: activeAlertsList,
    acknowledgeAlert,
    activeScenario,
    setScenario: applyScenario,
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
