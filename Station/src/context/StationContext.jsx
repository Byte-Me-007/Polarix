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

  const applyScenario = (scenarioKey) => {
    setActiveScenario(scenarioKey);
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
      setLastUpdated(new Date());
    }
  };

  const value = {
    activeStation,
    setActiveStation: handleStationChange,
    stationConfig,
    config: stationConfig,
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
